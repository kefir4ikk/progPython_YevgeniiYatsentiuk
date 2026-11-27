"""Синтаксичний розбір рядків журналу.

Формат запису (поля розділені крапкою з комою, пробіли навколо дозволені)::

    <вузол> ; <регістр стану> ; <значення> ; <часова мітка>
    TMP-001 ; 0x0000 ; 41.25 ; 2026-03-14T10:00:00
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Iterator, NamedTuple

from .exceptions import (
    InvalidTimestampError,
    MalformedRecordError,
    RecordError,
)
from .sensors import BaseSensor, create_sensor

__all__ = [
    "RECORD_PATTERN",
    "RawRecord",
    "ParseStats",
    "split_record",
    "parse_line",
    "parse_stream",
]

RECORD_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<node>(?P<kind>[A-Z]{3})-(?P<num>\d{3,4}))      # TMP-001
    \s*;\s*
    (?P<status>0[xX][0-9A-Fa-f]{4})                    # 0x00A5, 16 біт
    \s*;\s*
    (?P<value>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)     # -3.5, 12, 1e3
    \s*;\s*
    (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})        # ISO 8601
    \s*$
    """,
    re.VERBOSE,
)


class RawRecord(NamedTuple):
    """Незмінний кортеж полів до побудови об'єкта сенсора."""

    node_id: str
    status: int
    value: float
    timestamp: datetime


@dataclass
class ParseStats:
    """Лічильники розбору; заповнюються генератором на ходу."""

    lines: int = 0
    skipped: int = 0
    records: int = 0
    rejected: list[RecordError] = field(default_factory=list)

    @property
    def candidates(self) -> int:
        """Скільки рядків претендували на звання запису."""
        return self.records + len(self.rejected)


def split_record(line: str) -> RawRecord:
    """Перевіряє формат регулярним виразом і вилучає параметри."""
    match = RECORD_PATTERN.match(line)
    if match is None:
        raise MalformedRecordError(
            "рядок не відповідає формату "
            "«ВУЗОЛ;0xRRRR;значення;РРРР-ММ-ДДTГГ:ХХ:СС»")
    try:
        stamp = datetime.fromisoformat(match["ts"])
    except ValueError as exc:
        raise InvalidTimestampError(
            f"неіснуюча часова мітка {match['ts']!r}") from exc
    return RawRecord(
        node_id=match["node"],
        status=int(match["status"], 16),
        value=float(match["value"]),
        timestamp=stamp,
    )


def parse_line(line: str, line_no: int = 0) -> BaseSensor:
    """Повний розбір одного рядка до об'єкта сенсора."""
    try:
        raw = split_record(line)
        return create_sensor(*raw)
    except RecordError as exc:
        exc.line_no = line_no or None
        exc.raw = line
        raise


def parse_stream(lines: Iterable[str], /, *, strict: bool = False,
                 stats: ParseStats | None = None) -> Iterator[BaseSensor]:
    """Генератор: по одному об'єкту сенсора на коректний рядок.

    Порожні рядки та коментарі (``#``) пропускаються. Пошкоджений запис
    у звичайному режимі потрапляє до ``stats.rejected``, а в суворому
    (``strict=True``) — перериває розбір.
    """
    stats = stats if stats is not None else ParseStats()
    for line_no, line in enumerate(lines, start=1):
        stats.lines += 1
        text = line.strip()
        if not text or text.startswith("#"):
            stats.skipped += 1
            continue
        try:
            sensor = parse_line(text, line_no)
        except RecordError as exc:
            if strict:
                raise
            stats.rejected.append(exc)
            continue
        stats.records += 1
        yield sensor