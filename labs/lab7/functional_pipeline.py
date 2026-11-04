"""
Лабораторна робота № 7. Модуль 1. Варіант 2.
Калькулятор метрик надійності вузлів із варіативною сигнатурою (*args, **kwargs),
валідацією вхідних даних та багатокритеріальне lambda-сортування вузлів
за правилом [CPU_Usage (спадання), RAM_Free (зростання)].

Метрики надійності за експоненційною моделлю відмов:
    MTBF = (1/n) * sum(T_i)            середнє напрацювання на відмову, год
    A    = MTBF / (MTBF + MTTR)        коефіцієнт готовності
    lam  = 1 / MTBF                    інтенсивність відмов, 1/год
    R(t) = exp(-lam * t)               ймовірність безвідмовної роботи за час t
Освітній компонент: Програмування на Python.
"""

import math
import time
from typing import Any, Callable

REPORT_WIDTH: int = 88
HOURS_PER_YEAR: float = 8760.0
ALLOWED_OPTIONS: frozenset[str] = frozenset({"mttr_hours", "mission_time_h", "strict"})


def calculate_reliability_metrics(*intervals_h: float, **options: Any) -> dict[str, float]:
    """
    Обчислює метрики надійності вузла.
    *intervals_h - довільна кількість інтервалів напрацювання між відмовами (години).
    **options    - опції: mttr_hours (за замовчуванням 2.0), mission_time_h (720.0),
                   strict (False: некоректні інтервали пропускаються, True: викликають ValueError).
    Повертає структурований словник метрик.
    """
    # Перевірка імен опцій: **options приймає будь-які імена, тому опечатки ловимо вручну
    unknown = set(options) - ALLOWED_OPTIONS
    if unknown:
        raise TypeError(f"Невідомі опції: {sorted(unknown)}")

    # Значення за замовчуванням
    mttr_hours = options.get("mttr_hours", 2.0)
    mission_time_h = options.get("mission_time_h", 720.0)
    strict = options.get("strict", False)

    if mttr_hours <= 0 or mission_time_h <= 0:
        raise ValueError("mttr_hours та mission_time_h повинні бути строго додатними.")

    valid: list[float] = []
    for idx, value in enumerate(intervals_h, start=1):
        # bool є підкласом int, тому True/False відкидаємо окремо
        is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
        if not is_number or not math.isfinite(value) or value <= 0:
            if strict:
                raise ValueError(f"Інтервал #{idx} ({value!r}) некоректний.")
            print(f"Попередження: інтервал #{idx} ({value!r}) некоректний і пропущений.")
            continue
        valid.append(float(value))

    if not valid:
        raise ValueError("Немає жодного коректного інтервалу напрацювання.")

    mtbf = sum(valid) / len(valid)
    failure_rate = 1.0 / mtbf
    availability = mtbf / (mtbf + mttr_hours)
    reliability = math.exp(-failure_rate * mission_time_h)

    return {
        "samples": len(valid),
        "skipped": len(intervals_h) - len(valid),
        "mtbf_h": mtbf,
        "mttr_h": float(mttr_hours),
        "failure_rate": failure_rate,
        "availability": availability,
        "reliability": reliability,
        "downtime_year_h": (1.0 - availability) * HOURS_PER_YEAR,
    }


def make_call_counter() -> Callable[[], int]:
    """
    Замикання (Enclosing scope): змінна count живе в області видимості make_call_counter,
    а оператор nonlocal дозволяє внутрішній функції змінювати її без виходу в глобальний простір.
    """
    count = 0

    def increment(step: int = 1) -> int:
        """Збільшує лічильник на step (0 - лише прочитати поточне значення)."""
        nonlocal count
        count += step
        return count

    return increment


def build_node_reports(nodes: list[tuple], mission_time_h: float) -> list[dict]:
    """
    Для кожного вузла викликає калькулятор метрик, розпаковуючи кортеж інтервалів через *
    та передаючи опції іменованими аргументами. Вузли без валідних даних виключаються.
    Формат вузла: (node_id, cpu_usage, ram_free_gb, mttr_hours, intervals_tuple).
    """
    tick = make_call_counter()
    reports = []
    for node_id, cpu_usage, ram_free_gb, mttr, intervals in nodes:
        try:
            metrics = calculate_reliability_metrics(
                *intervals, mttr_hours=mttr, mission_time_h=mission_time_h
            )
        except ValueError as err:
            print(f"Вузол {node_id} виключено з аналізу: {err}")
            continue
        tick()
        reports.append({"node_id": node_id, "cpu_usage": cpu_usage,
                        "ram_free_gb": ram_free_gb, **metrics})
    print(f"Виконано обчислень метрик (nonlocal-лічильник): {tick(0)}")
    return reports


def print_report_table(sorted_reports: list[dict]) -> None:
    """Виводить таблицю вузлів, відсортованих за [CPU desc, RAM_Free asc]."""
    header = (f"| {'№':^3} | {'Вузол':^11} | {'CPU, %':^7} | {'RAM, ГБ':^9} | {'MTBF, год':^9} | "
              f"{'MTTR':^6} | {'A, %':^9} | {'R(t), %':^9} |")
    print("=" * REPORT_WIDTH)
    print(f"{'МЕТРИКИ НАДІЙНОСТІ ВУЗЛІВ (СОРТУВАННЯ: CPU ↓, RAM_FREE ↑)':^{REPORT_WIDTH}}")
    print("=" * REPORT_WIDTH)
    print(header)
    print("-" * REPORT_WIDTH)
    for idx, rec in enumerate(sorted_reports, start=1):
        print(f"| {idx:^3d} | {rec['node_id']:<11} | {rec['cpu_usage']:^7.1f} | "
              f"{rec['ram_free_gb']:^9.1f} | {rec['mtbf_h']:^9.1f} | {rec['mttr_h']:^6.1f} | "
              f"{rec['availability'] * 100:^9.3f} | {rec['reliability'] * 100:^9.2f} |")
    print("=" * REPORT_WIDTH)


def main() -> None:
    """Головна функція демонстрації варіативних сигнатур та lambda-сортування."""
    t_start = time.perf_counter()
    mission_time_h = 720.0   # місія: 30 діб безперервної роботи

    # (node_id, CPU_Usage %, RAM_Free ГБ, MTTR год, інтервали напрацювання між відмовами, год)
    raw_nodes = [
        ("NODE-01", 91.4, 1.8, 2.0, (702.0, 815.5, 640.0, 910.2, 788.4)),
        ("NODE-02", 76.2, 6.4, 3.0, (1200.0, 1350.5, 980.0)),
        ("NODE-03", 76.2, 3.2, 1.5, (450.0, 520.5, 610.0, 380.0)),      # CPU як у NODE-02
        ("NODE-04", 55.0, 12.0, 4.0, (2100.0, 1850.0, 2400.5)),
        ("NODE-05", 83.7, 4.5, 2.5, (300.0, -50.0, 410.0, "abc", 280.0)),  # два некоректні
        ("NODE-06", 33.3, 14.2, 2.0, ()),                                # немає даних
        ("NODE-07", 68.9, 8.0, 2.0, (1500.0,)),
    ]

    print("=" * REPORT_WIDTH)
    print(f"{'ВАРІАНТ 2. КАЛЬКУЛЯТОР МЕТРИК НАДІЙНОСТІ ТА LAMBDA-СОРТУВАННЯ':^{REPORT_WIDTH}}")
    print("=" * REPORT_WIDTH)
    print(f"Вхідних вузлів: {len(raw_nodes)}, час місії t = {mission_time_h:g} год\n")

    # 1. Обчислення метрик (*args через розпакування кортежу, **kwargs через іменовані опції)
    reports = build_node_reports(raw_nodes, mission_time_h)
    print(f"Вузлів у звіті: {len(reports)}\n")

    # 2. Багатокритеріальне сортування: CPU за спаданням, RAM_Free за зростанням
    sorted_reports = sorted(reports, key=lambda r: (-r["cpu_usage"], r["ram_free_gb"]))
    print_report_table(sorted_reports)

    # 3. Функції вищого порядку: filter, map, min з lambda
    overloaded = list(filter(lambda r: r["cpu_usage"] > 80.0, sorted_reports))
    overloaded_ids = list(map(lambda r: r["node_id"], overloaded))
    weakest = min(reports, key=lambda r: r["availability"])
    print(f"Вузли з CPU > 80 % (filter + map):        {overloaded_ids}")
    print(f"Найменша готовність A (min + lambda):     {weakest['node_id']} "
          f"({weakest['availability'] * 100:.3f}%)")
    print(f"Простій найгіршого вузла за рік:          {weakest['downtime_year_h']:.1f} год")

    # 4. Захист від опечаток в іменах опцій
    try:
        calculate_reliability_metrics(100.0, 120.0, mission_tim_h=500.0)
    except TypeError as err:
        print(f"Перехоплено TypeError: {err}")

    # 5. Режим strict=True перетворює некоректний інтервал на виняток
    try:
        calculate_reliability_metrics(100.0, -5.0, strict=True)
    except ValueError as err:
        print(f"Перехоплено ValueError (strict=True): {err}")

    elapsed = time.perf_counter() - t_start
    print(f"\nЧас виконання функціонального конвеєра: {elapsed * 1000:.3f} мс\n")


if __name__ == "__main__":
    main()
