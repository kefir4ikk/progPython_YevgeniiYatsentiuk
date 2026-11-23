"""
РГР. Модуль reporting: текстове подання результатів (таблиці та діаграма Ганта для консолі).
Освітній компонент: Програмування на Python.
"""

from __future__ import annotations

from .models import KIND_IDLE, KIND_RUN, ScheduleResult, Segment, Workload

__all__ = ["render_workload", "render_table", "render_summary", "render_gantt",
           "render_comparison"]


def render_workload(workload: Workload) -> str:
    """Таблиця вхідного навантаження."""
    lines = [f"Вхідне навантаження: процесів = {len(workload)}, B = {workload.total_burst}",
             f"{'PID':<8}{'надходж.':>10}{'тривал.':>10}"]
    lines += [f"{p.pid:<8}{p.arrival_time:>10}{p.burst_time:>10}" for p in workload]
    return "\n".join(lines)


def render_table(result: ScheduleResult) -> str:
    """Таблиця показників по кожному процесу."""
    header = (f"{'PID':<8}{'a':>6}{'b':>6}{'s':>6}{'C':>7}{'T':>7}{'W':>7}{'R':>7}")
    lines = [header, "-" * len(header)]
    for item in result:
        lines.append(f"{item.pid:<8}{item.arrival:>6}{item.burst:>6}{item.first_start:>6}"
                     f"{item.completion:>7}{item.turnaround:>7}{item.waiting:>7}{item.response:>7}")
    return "\n".join(lines)


def render_summary(result: ScheduleResult) -> str:
    """Агреговані показники одного прогону."""
    return "\n".join([
        f"Алгоритм: {result.label}   (параметри: {result.parameters})",
        f"  середній час очікування   W = {result.avg_waiting:8.3f}",
        f"  середній час обороту      T = {result.avg_turnaround:8.3f}",
        f"  середній час відгуку      R = {result.avg_response:8.3f}",
        f"  середній нормований оборот   = {result.avg_slowdown:8.3f}",
        f"  максимальне очікування       = {result.max_waiting:8d}",
        f"  інтервал спостереження       = {result.makespan:8d}",
        f"  завантаження CPU          U = {result.utilization:7.2f} %",
        f"  пропускна здатність          = {result.throughput:8.4f} проц./од.",
        f"  перемикань контексту         = {result.context_switches:8d}"
        f"  (час на перемикання {result.switch_time}, простій {result.idle_time})",
    ])


def _label(segment: Segment) -> str:
    if segment.kind == KIND_RUN:
        return segment.pid or "?"
    return "idle" if segment.kind == KIND_IDLE else "cs"


def render_gantt(result: ScheduleResult, max_width: int = 100) -> str:
    """Діаграма Ганта: рядок блоків і рядок часових позначок; довгі діаграми переносяться."""
    segments = result.segments
    span = max(result.end_time - result.start_time, 1)
    scale = min(1.0, (max_width - len(segments) - 1) / span) if len(segments) < max_width else 0.0

    cells: list[tuple[str, str]] = []              # (блок, підпис початку)
    for seg in segments:
        label = _label(seg)
        width = max(len(label) + 2, len(str(seg.start)) + 1, round(seg.duration * scale))
        cells.append((label.center(width, "-" if seg.kind == KIND_RUN else "."),
                      str(seg.start)))

    rows: list[str] = []
    bar, ticks, used = "|", " ", 1
    for (block, tick), seg in zip(cells, segments):
        if used + len(block) + 1 > max_width and used > 1:
            rows += [bar, ticks]
            bar, ticks, used = "|", " ", 1
        bar += block + "|"
        ticks += tick.ljust(len(block) + 1)
        used += len(block) + 1
    ticks = ticks.rstrip() + f" {result.end_time}"
    rows += [bar, ticks]
    return "\n".join(rows)


def render_comparison(results: list[ScheduleResult]) -> str:
    """Порівняльна таблиця алгоритмів; найкращий за середнім очікуванням позначено '*'."""
    best = min(results)
    header = (f"{'':2}{'Алгоритм':<12}{'W':>9}{'T':>9}{'R':>9}{'W_max':>8}"
              f"{'U,%':>8}{'CS':>7}{'L':>7}")
    lines = [header, "-" * len(header)]
    for res in results:
        mark = "*" if res is best else " "
        lines.append(f"{mark:<2}{res.label:<12}{res.avg_waiting:>9.2f}{res.avg_turnaround:>9.2f}"
                     f"{res.avg_response:>9.2f}{res.max_waiting:>8}{res.utilization:>8.1f}"
                     f"{res.context_switches:>7}{res.makespan:>7}")
    lines.append("* - найменший середній час очікування W")
    return "\n".join(lines)
