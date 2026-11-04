"""
Лабораторна робота № 7. Модуль 2. Варіант 2.
Рекурсивне сортування злиттям (Merge Sort): рекурсивний поділ масиву навпіл
та злиття двох впорядкованих підмасивів. Програмний контроль глибини стека,
порівняння з ітеративним (висхідним) аналогом і з вбудованим Timsort.

Рекурентне співвідношення: T(n) = 2 * T(n / 2) + Theta(n)  =>  Theta(n log n)
Глибина рекурсії: D(n) = ceil(log2 n) + 1
Освітній компонент: Програмування на Python.
"""

import random
import sys
import time

REPORT_WIDTH: int = 88


class RecursionDepthTracker:
    """Моніторинг та захист глибини рекурсивного стека; також рахує виклики й порівняння."""

    def __init__(self, max_allowed_depth: int = 500) -> None:
        self.current_depth = 0
        self.max_observed_depth = 0
        self.max_allowed_depth = max_allowed_depth
        self.calls = 0
        self.comparisons = 0

    def enter(self) -> None:
        """Фіксує вхід у новий рекурсивний кадр і перевіряє безпечний ліміт."""
        self.current_depth += 1
        self.calls += 1
        self.max_observed_depth = max(self.max_observed_depth, self.current_depth)
        if self.current_depth > self.max_allowed_depth:
            raise RecursionError(
                f"Перевищено безпечний ліміт глибини: {self.current_depth} > {self.max_allowed_depth}"
            )

    def leave(self) -> None:
        """Фіксує вихід зі стекового кадру."""
        self.current_depth -= 1


def merge(left: list[int], right: list[int], tracker: RecursionDepthTracker | None = None) -> list[int]:
    """
    Зливає два впорядковані підмасиви в один за O(len(left) + len(right)).
    Умова left[i] <= right[j] зберігає стійкість сортування (рівні елементи не міняються місцями).
    """
    merged: list[int] = []
    i = j = 0
    while i < len(left) and j < len(right):
        if tracker is not None:
            tracker.comparisons += 1
        if left[i] <= right[j]:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    # Один із підмасивів вичерпано: решту іншого дописуємо без порівнянь
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


def merge_sort_recursive(arr: list[int], tracker: RecursionDepthTracker) -> list[int]:
    """Рекурсивне сортування злиттям з обліком глибини стека."""
    tracker.enter()
    try:
        # Базовий випадок: масив з 0 або 1 елемента вже впорядкований
        if len(arr) <= 1:
            return list(arr)

        mid = len(arr) // 2
        left_sorted = merge_sort_recursive(arr[:mid], tracker)    # лівий підмасив
        right_sorted = merge_sort_recursive(arr[mid:], tracker)   # правий підмасив
        return merge(left_sorted, right_sorted, tracker)
    finally:
        tracker.leave()


def merge_sort_iterative(arr: list[int]) -> list[int]:
    """
    Ітеративне висхідне (bottom-up) сортування злиттям без рекурсії.
    Спочатку зливаються сусідні відрізки довжини 1, потім 2, 4, 8 тощо.
    Використовує два буфери однакового розміру, глибина стека константна.
    """
    n = len(arr)
    src, dst = list(arr), [0] * n
    width = 1
    while width < n:
        for lo in range(0, n, 2 * width):
            mid, hi = min(lo + width, n), min(lo + 2 * width, n)
            i, j, k = lo, mid, lo
            while i < mid and j < hi:
                if src[i] <= src[j]:
                    dst[k] = src[i]
                    i += 1
                else:
                    dst[k] = src[j]
                    j += 1
                k += 1
            dst[k:hi] = src[i:mid] + src[j:hi]   # одна з частин порожня
        src, dst = dst, src
        width *= 2
    return src


def theoretical_depth(n: int) -> int:
    """Теоретична глибина рекурсії D(n) = ceil(log2 n) + 1 (для n >= 1)."""
    return (n - 1).bit_length() + 1


def recursive_sum(n: int) -> int:
    """Лінійна рекурсія глибиною n: приклад небезпечної рекурсії, що вичерпує стек."""
    return 0 if n == 0 else n + recursive_sum(n - 1)


def best_time_ms(func, data: list[int], repeats: int = 3) -> float:
    """Повертає найкращий з repeats замірів часу виконання func(data) у мілісекундах."""
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        func(data)
        best = min(best, time.perf_counter() - t0)
    return best * 1000.0


def demo_small_array() -> None:
    """Демонстрація на масиві з 20 елементів із моніторингом стека."""
    print(f"Системний ліміт глибини стека CPython: {sys.getrecursionlimit()} кадрів")
    random.seed(2026)
    test_array = [random.randint(-100, 100) for _ in range(20)]
    print(f"Початковий масив (N = {len(test_array)}):   {test_array}")
    print("-" * REPORT_WIDTH)

    tracker = RecursionDepthTracker(max_allowed_depth=200)
    result = merge_sort_recursive(test_array, tracker)
    print(f"Відсортований масив:               {result}")
    print(f"Верифікація (== sorted):           {str(result == sorted(test_array)).upper()}")
    print(f"Ітеративний аналог збігається:     {str(merge_sort_iterative(test_array) == result).upper()}")
    print(f"Максимальна глибина D:             {tracker.max_observed_depth} кадрів "
          f"(теорія: {theoretical_depth(len(test_array))})")
    print(f"Рекурсивних викликів:              {tracker.calls} (теорія: 2N - 1 = {2 * len(test_array) - 1})")
    print(f"Порівнянь елементів у злиттях:     {tracker.comparisons}")
    print("-" * REPORT_WIDTH)

    # Захист від переповнення: штучно низький безпечний ліміт
    strict_tracker = RecursionDepthTracker(max_allowed_depth=4)
    try:
        merge_sort_recursive(test_array, strict_tracker)
    except RecursionError as err:
        print(f"Перехоплено RecursionError (ліміт 4): {err}")

    # Для порівняння: лінійна рекурсія глибиною 5000 вичерпує системний стек
    try:
        recursive_sum(5000)
    except RecursionError:
        print(f"recursive_sum(5000) -> RecursionError: глибина перевищила {sys.getrecursionlimit()}")
    print(f"Merge Sort для N = 1 000 000 потребує лише D = {theoretical_depth(1_000_000)} кадрів")


def demo_benchmark() -> None:
    """Порівняння швидкодії рекурсивного, ітеративного сортування злиттям та sorted()."""
    print(f"\n{'ПОРІВНЯННЯ ШВИДКОДІЇ (найкращий із 3 замірів)':^{REPORT_WIDTH}}")
    print("-" * REPORT_WIDTH)
    print(f"| {'N':^8} | {'Рекурс., мс':^12} | {'Ітерат., мс':^12} | {'sorted, мс':^12} | "
          f"{'D':^5} | {'D теор.':^7} | {'Порівнянь':^10} |")
    print("-" * REPORT_WIDTH)

    random.seed(7)
    for n in (1_000, 5_000, 20_000, 100_000):
        data = [random.randint(-10**6, 10**6) for _ in range(n)]

        tracker = RecursionDepthTracker(max_allowed_depth=100)
        rec_result = merge_sort_recursive(data, tracker)
        assert rec_result == sorted(data) == merge_sort_iterative(data), "Помилка сортування!"

        t_rec = best_time_ms(lambda d: merge_sort_recursive(d, RecursionDepthTracker(100)), data)
        t_iter = best_time_ms(merge_sort_iterative, data)
        t_builtin = best_time_ms(sorted, data)

        print(f"| {n:>8d} | {t_rec:>12.3f} | {t_iter:>12.3f} | {t_builtin:>12.3f} | "
              f"{tracker.max_observed_depth:^5d} | {theoretical_depth(n):^7d} | {tracker.comparisons:>10d} |")
    print("=" * REPORT_WIDTH + "\n")


def main() -> None:
    """Головна точка входу: демонстрація та профілювання сортування злиттям."""
    print("=" * REPORT_WIDTH)
    print(f"{'ВАРІАНТ 2. РЕКУРСИВНЕ СОРТУВАННЯ ЗЛИТТЯМ (MERGE SORT)':^{REPORT_WIDTH}}")
    print("=" * REPORT_WIDTH)
    demo_small_array()
    demo_benchmark()


if __name__ == "__main__":
    main()
