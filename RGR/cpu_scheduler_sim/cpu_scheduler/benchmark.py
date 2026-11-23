"""
РГР. Модуль benchmark: генерація навантаження та вимірювання швидкодії через time.perf_counter().

Емпірична оцінка складності: показник степеня k у залежності t ~ n^k визначається нахилом
лінійної регресії в логарифмічних координатах (statistics.linear_regression).
Освітній компонент: Програмування на Python.
"""

from __future__ import annotations

import math
import random
import statistics
import time

from .models import Process, Workload
from .schedulers import BaseScheduler, FIFOScheduler, RoundRobinScheduler

__all__ = ["generate_workload", "time_scheduler", "run_benchmark", "estimate_exponent",
           "workload_to_text"]


def generate_workload(n: int, seed: int = 1, max_gap: int = 3, max_burst: int = 20) -> Workload:
    """Псевдовипадкове навантаження з n процесів; seed робить експеримент відтворюваним."""
    rng = random.Random(seed)
    arrival = 0
    processes = []
    for index in range(1, n + 1):
        arrival += rng.randint(0, max_gap)
        processes.append(Process(f"P{index}", arrival, rng.randint(1, max_burst)))
    return Workload(processes)


def workload_to_text(workload: Workload) -> str:
    """Текстове подання навантаження у форматі ключ-значення (для збереження у файл)."""
    return "\n".join(f"{p.pid} arrival={p.arrival_time} burst={p.burst_time}"
                     for p in workload) + "\n"


def time_scheduler(scheduler: BaseScheduler, workload: Workload, repeats: int = 3) -> float:
    """Найкращий з repeats вимірів часу одного прогону, секунди."""
    best = math.inf
    for _ in range(max(1, repeats)):
        started = time.perf_counter()
        scheduler.schedule(workload)
        best = min(best, time.perf_counter() - started)
    return best


def run_benchmark(sizes: list[int], quantum: int = 4, repeats: int = 3, seed: int = 1,
                  switch_cost: int = 0) -> list[dict]:
    """Вимірює FIFO та RR для кожного розміру; повертає рядки {n, algorithm, seconds, slices}."""
    rows: list[dict] = []
    for n in sizes:
        workload = generate_workload(n, seed=seed)
        for scheduler in (FIFOScheduler(switch_cost), RoundRobinScheduler(quantum, switch_cost)):
            seconds = time_scheduler(scheduler, workload, repeats)
            slices = scheduler.schedule(workload).slices
            rows.append({"n": n, "algorithm": scheduler.name, "seconds": seconds,
                         "slices": slices})
    return rows


def estimate_exponent(sizes: list[int], seconds: list[float]) -> float:
    """Показник k у моделі t = c * n^k (нахил прямої в координатах log-log)."""
    xs = [math.log(n) for n in sizes]
    ys = [math.log(t) for t in seconds]
    return statistics.linear_regression(xs, ys).slope
