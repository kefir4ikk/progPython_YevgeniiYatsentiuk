"""
Еталонний (референсний) симулятор: простий покроковий (tick-by-tick) алгоритм складності O(L),
написаний незалежно від подієвого планувальника пакета. Використовується для перехресної
перевірки: на великій кількості випадкових наборів обидві реалізації мають давати однакові
моменти завершення, перших запусків і лічильник перемикань.
"""

from __future__ import annotations


def reference_simulate(procs: list[tuple[str, int, int]], quantum: int | None, sigma: int = 0):
    """
    procs   - список (pid, arrival, burst) у порядку введення;
    quantum - None для FIFO, ціле число для Round Robin;
    sigma   - вартість перемикання контексту.
    Повертає (completion, first_start, switches, ticks), де ticks - позначка кожної одиниці часу.
    """
    t = min(a for _, a, _ in procs)
    order = sorted(range(len(procs)), key=lambda i: procs[i][1])      # стабільно за надходженням
    incoming = [procs[i] for i in order]
    remaining = {pid: b for pid, _, b in procs}
    queue: list[str] = []
    next_in = 0
    completion: dict[str, int] = {}
    first_start: dict[str, int] = {}
    ticks: list[str] = []
    switches = 0

    running: str | None = None
    slice_left = 0
    cs_left = 0
    last_pid: str | None = None
    preempted: str | None = None

    while len(completion) < len(procs):
        # Допуск процесів, що надійшли до моменту t; витіснений - після них
        while next_in < len(incoming) and incoming[next_in][1] <= t:
            queue.append(incoming[next_in][0])
            next_in += 1
        if preempted is not None:
            queue.append(preempted)
            preempted = None

        if running is None and cs_left == 0 and queue:
            running = queue.pop(0)
            if last_pid is not None and last_pid != running:
                switches += 1
                cs_left = sigma
            slice_left = remaining[running] if quantum is None else min(quantum, remaining[running])

        if running is None and cs_left == 0:       # нікого виконувати: простій
            ticks.append("IDLE")
            last_pid = None
            t += 1
            continue

        if cs_left > 0:                            # оплата перемикання контексту
            ticks.append("CS")
            cs_left -= 1
            t += 1
            continue

        first_start.setdefault(running, t)
        ticks.append(running)
        remaining[running] -= 1
        slice_left -= 1
        last_pid = running
        t += 1
        if remaining[running] == 0:
            completion[running] = t
            running = None
        elif slice_left == 0:
            preempted = running
            running = None

    return completion, first_start, switches, ticks
