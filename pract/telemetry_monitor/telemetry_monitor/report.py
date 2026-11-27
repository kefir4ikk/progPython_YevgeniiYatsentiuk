"""Формування підсумкового звіту."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import IO, Iterator

from .analytics import Aggregate
from .flags import decode_flags, quality_of
from .parser import ParseStats

__all__ = ["Summary", "iter_report_lines", "write_report"]


@dataclass
class Summary:
    """Усе, що потрібно для звіту."""

    source: str
    parse: ParseStats
    agg: Aggregate

    @property
    def rejected_ratio(self) -> float:
        candidates = self.parse.candidates
        return len(self.parse.rejected) / candidates if candidates else 0.0


def _flag_names(mask: int) -> str:
    names = [flag.name for flag in decode_flags(mask)]
    return ", ".join(names) if names else "—"


def iter_report_lines(summary: Summary) -> Iterator[str]:
    """Генератор рядків звіту: повний текст у пам'яті не будується."""
    parse, agg = summary.parse, summary.agg
    yield "ЗВІТ ПРО ТЕЛЕМЕТРІЮ СЕНСОРІВ МЕРЕЖІ"
    yield "=" * 72
    yield f"Журнал:               {summary.source}"
    yield f"Рядків прочитано:     {parse.lines}"
    yield f"Службових рядків:     {parse.skipped}"
    yield f"Коректних записів:    {parse.records}"
    yield (f"Відхилено записів:    {len(parse.rejected)} "
           f"({summary.rejected_ratio:.1%})")
    yield f"Враховано у вибірці:  {agg.total}"
    yield f"Унікальних вузлів:    {len(agg.nodes)}"
    crit = ", ".join(sorted(agg.critical_nodes)) or "немає"
    yield f"Вузли з відмовами:    {crit}"

    yield ""
    yield "Статистика за вузлами"
    yield "-" * 72
    yield (f"{'Вузол':<9}{'N':>4}{'Мін':>9}{'Сер':>9}{'Макс':>9}"
           f"{'Крит.':>7}  Прапорці")
    for st in agg.stats:
        yield (f"{st.node_id:<9}{st.count:>4}{st.minimum:>9.2f}"
               f"{st.mean:>9.2f}{st.maximum:>9.2f}{st.critical_count:>7}"
               f"  {_flag_names(st.flags_seen)}")

    yield ""
    yield "Частота апаратних прапорців"
    yield "-" * 72
    if agg.flag_histogram:
        for name, count in agg.flag_histogram.most_common():
            yield f"{name:<16}{count:>4}"
    else:
        yield "прапорців не зафіксовано"

    yield ""
    yield "Критичні події"
    yield "-" * 72
    if not agg.critical_events:
        yield "немає"
    for sensor in agg.critical_events:
        yield (f"{sensor.timestamp:%H:%M:%S} {sensor.node_id} "
               f"{sensor.value:g} {sensor.unit} "
               f"[{sensor.status:#06x}, якість {quality_of(sensor.status)}]")
        for reason in sensor.diagnose():
            yield f"    - {reason}"

    yield ""
    yield "Відхилені записи"
    yield "-" * 72
    if not parse.rejected:
        yield "немає"
    else:
        by_code = Counter(err.code for err in parse.rejected)
        yield "за кодами: " + ", ".join(
            f"E{code}: {n}" for code, n in sorted(by_code.items()))
        for err in parse.rejected:
            yield str(err)
            yield f"    {err.raw!r}"


def write_report(summary: Summary, handle: IO[str]) -> None:
    for line in iter_report_lines(summary):
        handle.write(line + "\n")