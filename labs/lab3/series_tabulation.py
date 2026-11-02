"""
Лабораторна робота № 3. Модуль 2. Варіант 2.
Чисельне табулювання кусочної функції на [-3, 3] з кроком h = 0.25 (цикл for)
та обчислення ряду Тейлора для sin(x) з точністю eps = 1e-7 (цикл while)
за допомогою рекурентного співвідношення.

sin(x) = sum_{k=0}^{inf} (-1)^k x^(2k+1) / (2k+1)!
a_0 = x,   a_k = a_{k-1} * (-x^2) / (2k * (2k + 1))

Освітній компонент: Програмування на Python.
"""

import math
import time

from branching_logic import classify_branch, evaluate_piecewise_function

# Параметри індивідуального варіанта 2
A_START: float = -3.0
B_END: float = 3.0
H_STEP: float = 0.25
EPSILON: float = 1e-7
MAX_ITERATIONS: int = 1000


def tabulate_function(start_a: float, end_b: float, step_h: float) -> list[tuple[float, float, str]]:
    """
    Табулює f(x) на відрізку [a, b] з кроком h параметричним циклом for.
    Вузли обчислюються як x_i = a + i * h, i = 0..N, де N = floor((b - a) / h).
    Повертає список кортежів (x_i, y_i, назва_гілки).
    """
    if step_h <= 0.0:
        raise ValueError("Крок табулювання h повинен бути строго додатним.")
    if start_a > end_b:
        raise ValueError("Початкова межа a не може перевищувати кінцеву межу b.")

    # Мала добавка захищає від втрати останнього вузла через похибку округлення
    num_steps = int(math.floor((end_b - start_a) / step_h + 1e-9))

    table = []
    for i in range(num_steps + 1):
        x_i = start_a + i * step_h
        y_i = evaluate_piecewise_function(x_i)
        table.append((x_i, y_i, classify_branch(x_i)))
    return table


def compute_taylor_sin(
    x: float, epsilon: float = EPSILON, max_iterations: int = MAX_ITERATIONS
) -> tuple[float, int, float, float]:
    """
    Обчислює sin(x) сумуванням ряду Тейлора циклом while з рекурентним співвідношенням.
    Повертає кортеж (сума_ряду, кількість_ітерацій, еталон_math.sin, абсолютна_похибка).
    Цикл завершується, коли |a_k| < epsilon або досягнуто max_iterations.
    """
    if epsilon <= 0.0:
        raise ValueError("Точність epsilon повинна бути строго додатною.")

    k = 0
    a_k = x                 # a_0 = x
    series_sum = a_k

    while math.fabs(a_k) >= epsilon and k < max_iterations:
        k += 1
        # Рекурентний коефіцієнт R(k, x) = -x^2 / (2k * (2k + 1))
        a_k *= (-x * x) / (2.0 * k * (2.0 * k + 1.0))
        series_sum += a_k
    else:
        if k >= max_iterations:
            print(f"Попередження: досягнуто ліміт ітерацій ({max_iterations}) для x = {x:.4f}!")

    reference = math.sin(x)
    return series_sum, k, reference, math.fabs(series_sum - reference)


def print_tabulation_table(data: list[tuple[float, float, str]]) -> None:
    """Виводить таблицю табулювання."""
    sep = "=" * 65
    print(sep)
    print(f"{'ТАБЛИЦЯ ТАБУЛЮВАННЯ ФУНКЦІЇ f(x) НА [-3, 3], h = 0.25':^65}")
    print(sep)
    print(f"| {'№':^4} | {'Вузол x':^14} | {'Значення y = f(x)':^20} | {'Сегмент':^10} |")
    print("-" * 65)
    for idx, (x_val, y_val, tag) in enumerate(data, start=1):
        print(f"| {idx:^4} | {x_val:^14.4f} | {y_val:^20.8f} | {tag:^10} |")
    print(sep)


def main() -> None:
    """Демонстрація табулювання та підсумовування ряду."""
    print("\n" + "#" * 80)
    print(f"{'ВАРІАНТ 2. ТАБУЛЮВАННЯ ТА РЯД ТЕЙЛОРА ДЛЯ sin(x) (ЛБ №3)':^80}")
    print("#" * 80 + "\n")

    # 1. Табулювання
    table = tabulate_function(A_START, B_END, H_STEP)
    print_tabulation_table(table)
    print(f"Кількість вузлів: {len(table)}  (N = {len(table) - 1} кроків)")

    # 2. Ряд Тейлора
    print("\n" + "=" * 80)
    print(f"{'ОБЧИСЛЕННЯ РЯДУ ТЕЙЛОРА sin(x) ІЗ ТОЧНІСТЮ eps = 1e-7':^80}")
    print("=" * 80)
    print(f"| {'x':^8} | {'Сума ряду S(x)':^18} | {'Еталон math.sin':^18} | {'Ітер.':^6} | {'Похибка':^12} |")
    print("-" * 80)

    test_points = [-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0]
    all_within_eps = True
    for x_test in test_points:
        s_val, steps, ref, err = compute_taylor_sin(x_test)
        all_within_eps = all_within_eps and err < EPSILON
        print(f"| {x_test:^8.2f} | {s_val:^18.10f} | {ref:^18.10f} | {steps:^6} | {err:^12.4e} |")
    print("=" * 80)
    print(f"Похибка в усіх контрольних точках менша за eps = {EPSILON:g}: {all_within_eps}\n")


if __name__ == "__main__":
    t_start = time.perf_counter()
    main()
    elapsed = time.perf_counter() - t_start
    print(f"Загальний час виконання розрахунків: {elapsed * 1000:.3f} мс\n")
