"""Вимірювання для теоретичної частини (Завдання 3).

Запуск: python tools/measure.py
"""

from __future__ import annotations

import dis
import gc
import io
import sys
import timeit
import tracemalloc
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from telemetry_monitor.flags import set_bit_positions  # noqa: E402
from telemetry_monitor.parser import RECORD_PATTERN, parse_stream  # noqa: E402
from telemetry_monitor.sensors import (  # noqa: E402
    BaseSensor, FanSensor, TemperatureSensor, VoltageSensor)


def section(title: str) -> None:
    print(f"\n### {title}")


def show_mro() -> None:
    section("MRO")
    for cls in (TemperatureSensor, FanSensor, VoltageSensor):
        print(cls.__name__, "->", " > ".join(c.__name__
                                             for c in cls.__mro__))


def show_dis() -> None:
    section("dis(set_bit_positions)")
    buf = io.StringIO()
    dis.dis(set_bit_positions, file=buf)
    print(buf.getvalue())


def show_slots() -> None:
    section("__slots__ проти __dict__")

    class Plain:   # еквівалент без __slots__
        def __init__(self):
            self._node_id = "TMP-001"
            self._status = 0
            self._value = 1.0
            self._timestamp = datetime(2026, 3, 14)

    slotted = TemperatureSensor("TMP-001", 0, 1.0, datetime(2026, 3, 14))
    plain = Plain()
    size_slots = sys.getsizeof(slotted)
    size_plain = sys.getsizeof(plain) + sys.getsizeof(plain.__dict__)
    print(f"зі __slots__:  {size_slots} байт")
    print(f"зі __dict__:   {size_plain} байт")
    print(f"has __dict__:  {hasattr(slotted, '__dict__')}")


def show_refcount() -> None:
    section("лічильники посилань")
    data = [1, 2, 3]
    print("новий список:      ", sys.getrefcount(data) - 1)
    alias = data
    print("після alias = data:", sys.getrefcount(data) - 1)
    holder = (data, data)
    print("після кортежу:     ", sys.getrefcount(data) - 1)
    del alias, holder
    print("після del:         ", sys.getrefcount(data) - 1)
    a = 256
    b = int("256")
    c = 257
    d = int("257")
    print("256 is 256:", a is b, "| 257 is 257:", c is d)
    cycle = []
    cycle.append(cycle)
    del cycle
    print("циклічне сміття, зібрано GC:", gc.collect() >= 1)


def synth_lines(count: int) -> list[str]:
    kinds = ("TMP", "VLT", "FAN")
    return [f"{kinds[i % 3]}-{i % 50 + 1:03d};0xF000;{20 + i % 40}.5;"
            f"2026-03-14T10:{i // 60 % 60:02d}:{i % 60:02d}"
            for i in range(count)]


def show_generator_memory() -> None:
    section("генератор проти списку (200 000 рядків)")
    lines = synth_lines(200_000)

    tracemalloc.start()
    total = 0
    for sensor in parse_stream(lines):
        total += 1
    _, peak_gen = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    everything = list(parse_stream(lines))
    _, peak_list = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"генератор: пік {peak_gen / 1024:.0f} КіБ ({total} записів)")
    print(f"список:    пік {peak_list / 1024 / 1024:.1f} МіБ "
          f"({len(everything)} записів)")

    started = timeit.default_timer()
    count = sum(1 for _ in parse_stream(lines))
    elapsed = timeit.default_timer() - started
    print(f"швидкість розбору: {count / elapsed:,.0f} записів/с")


def show_lookup() -> None:
    section("пошук вузла: список проти множини/словника")
    for size in (100, 1000, 10000):
        names = [f"TMP-{i:04d}" for i in range(size)]
        as_set = set(names)
        as_dict = dict.fromkeys(names, 0)
        target = names[-1]
        t_list = timeit.timeit(lambda: target in names, number=2000)
        t_set = timeit.timeit(lambda: target in as_set, number=2000)
        t_dict = timeit.timeit(lambda: as_dict[target], number=2000)
        print(f"n={size:>6}: list {t_list / 2000 * 1e6:8.2f} мкс | "
              f"set {t_set / 2000 * 1e6:6.3f} мкс | "
              f"dict {t_dict / 2000 * 1e6:6.3f} мкс")


def show_regex() -> None:
    section("регулярний вираз")
    print("flags:", RECORD_PATTERN.flags, "| groups:",
          RECORD_PATTERN.groups, "| names:", list(RECORD_PATTERN.groupindex))
    line = "TMP-001;0x0000;40.0;2026-03-14T10:00:00"
    per_call = timeit.timeit(lambda: RECORD_PATTERN.match(line),
                             number=100_000) / 100_000
    print(f"match: {per_call * 1e6:.2f} мкс на рядок")
    for n in (1_000, 10_000, 100_000):
        evil = "TMP-001;0x0000;" + "1" * n + "x"
        t = timeit.timeit(lambda: RECORD_PATTERN.match(evil), number=20) / 20
        print(f"нескінченно довге значення, n={n:>6}: {t * 1e3:7.3f} мс")


def main() -> None:
    print(f"Python {sys.version.split()[0]}")
    show_mro()
    show_dis()
    show_slots()
    show_refcount()
    show_generator_memory()
    show_lookup()
    show_regex()
    assert issubclass(TemperatureSensor, BaseSensor)


if __name__ == "__main__":
    main()