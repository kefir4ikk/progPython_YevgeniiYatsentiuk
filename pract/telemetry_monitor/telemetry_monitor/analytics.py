"""Фільтрація та потокова агрегація телеметрії.

Вибір структур даних:

* кортеж  — запис і результат (незмінні, хешовані, економні);
* список  — події, які треба зберегти в порядку надходження;
* словник — групування за вузлом, пошук за ключем у середньому O(1);
* множина — унікальні вузли й вузли з критичними відмовами.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Iterator

from .flags import FLAGS_MASK
from .sensors import BaseSensor

__all__ = [
    "NodeStats",
    "Accumulator",
    "Aggregate",
    "filter_records",
    "aggregate",
]

Predicate = Callable[[BaseSensor], bool]
_LIMIT_KEYS = frozenset({"min_value", "max_value", "since", "until"})


def filter_records(records: Iterable[BaseSensor], /,
                   *predicates: Predicate,
                   kinds: Iterable[str] | None = None,
                   nodes: Iterable[str] | None = None,
                   critical_only: bool = False,
                   **limits: float | datetime) -> Iterator[BaseSensor]:
    """Генератор-фільтр з розширеною сигнатурою параметрів.

    ``records`` — лише позиційний; ``*predicates`` — довільні додаткові
    умови; ``kinds``/``nodes``/``critical_only`` — лише іменовані;
    ``**limits`` приймає min_value, max_value, since, until.
    """
    unknown = set(limits) - _LIMIT_KEYS
    if unknown:
        raise TypeError(f"невідомі обмеження: {', '.join(sorted(unknown))}")
    kind_set = frozenset(kinds) if kinds is not None else None
    node_set = frozenset(nodes) if nodes is not None else None
    for sensor in records:
        if kind_set is not None and sensor.kind not in kind_set:
            continue
        if node_set is not None and sensor.node_id not in node_set:
            continue
        if critical_only and not sensor.is_critical:
            continue
        if "min_value" in limits and sensor.value < limits["min_value"]:
            continue
        if "max_value" in limits and sensor.value > limits["max_value"]:
            continue
        if "since" in limits and sensor.timestamp < limits["since"]:
            continue
        if "until" in limits and sensor.timestamp > limits["until"]:
            continue
        if all(pred(sensor) for pred in predicates):
            yield sensor


@dataclass(frozen=True)
class NodeStats:
    """Незмінний підсумок по одному вузлу."""

    __slots__ = ("node_id", "kind", "unit", "count", "minimum", "maximum",
                 "mean", "critical_count", "flags_seen")

    node_id: str
    kind: str
    unit: str
    count: int
    minimum: float
    maximum: float
    mean: float
    critical_count: int
    flags_seen: int


class Accumulator:
    """Онлайн-накопичувач: пам'ять O(1) на вузол, а не O(кількість рядків)."""

    __slots__ = ("node_id", "kind", "unit", "count", "total", "minimum",
                 "maximum", "critical_count", "flags_seen")

    def __init__(self, sensor: BaseSensor) -> None:
        self.node_id = sensor.node_id
        self.kind = sensor.kind
        self.unit = sensor.unit
        self.count = 0
        self.total = 0.0
        self.minimum = sensor.value
        self.maximum = sensor.value
        self.critical_count = 0
        self.flags_seen = 0

    def add(self, sensor: BaseSensor) -> None:
        self.count += 1
        self.total += sensor.value
        self.minimum = min(self.minimum, sensor.value)
        self.maximum = max(self.maximum, sensor.value)
        self.critical_count += sensor.is_critical
        # об'єднання бітових масок побітовим «АБО»
        self.flags_seen |= sensor.status & FLAGS_MASK

    def freeze(self) -> NodeStats:
        return NodeStats(self.node_id, self.kind, self.unit, self.count,
                         self.minimum, self.maximum,
                         self.total / self.count, self.critical_count,
                         self.flags_seen)


@dataclass
class Aggregate:
    """Результат агрегації."""

    stats: tuple[NodeStats, ...]
    nodes: frozenset[str]
    critical_nodes: frozenset[str]
    critical_events: list[BaseSensor]
    flag_histogram: Counter
    total: int


def aggregate(records: Iterable[BaseSensor]) -> Aggregate:
    """Один прохід по потоку: словник вузол→накопичувач, множини, лічильник."""
    groups: dict[str, Accumulator] = {}
    critical_nodes: set[str] = set()
    events: list[BaseSensor] = []
    histogram: Counter = Counter()
    total = 0
    for sensor in records:
        total += 1
        acc = groups.get(sensor.node_id)
        if acc is None:
            acc = groups[sensor.node_id] = Accumulator(sensor)
        acc.add(sensor)
        for flag in sensor.flags:
            histogram[flag.name] += 1
        if sensor.is_critical:
            critical_nodes.add(sensor.node_id)
            events.append(sensor)
    stats = tuple(groups[key].freeze() for key in sorted(groups))
    return Aggregate(stats, frozenset(groups), frozenset(critical_nodes),
                     events, histogram, total)