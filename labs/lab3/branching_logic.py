"""
Лабораторна робота № 3. Модуль 1. Варіант 2.
Розгалужені алгоритми: обчислення кусочно-неперервної функції y = f(x)
за допомогою if-elif-else, класифікація гілки тернарним оператором,
демонстрація короткої схеми обчислення (short-circuit evaluation).

         | cos(x^2) + 1,   x < -1
f(x) =   | x^3 + 2x,       -1 <= x <= 1
         | cbrt(x - 1),    x > 1

Освітній компонент: Програмування на Python.
"""

import math
import time

# Межі гілок кусочної функції
LEFT_BOUND: float = -1.0
RIGHT_BOUND: float = 1.0


def evaluate_piecewise_function(x: float) -> float:
    """
    Обчислює f(x) за допомогою каскадної конструкції if-elif-else.
    Повертає дійсне значення функції у точці x.
    """
    if x < LEFT_BOUND:
        # Гілка 1: x < -1
        y = math.cos(x**2) + 1.0
    elif LEFT_BOUND <= x <= RIGHT_BOUND:
        # Гілка 2: -1 <= x <= 1
        y = x**3 + 2.0 * x
    else:
        # Гілка 3: x > 1. Тут x - 1 > 0, тому кубічний корінь визначений.
        y = (x - 1.0) ** (1.0 / 3.0)
    return y


def classify_branch(x: float) -> str:
    """Повертає назву гілки функції для точки x за допомогою вкладеного тернарного оператора."""
    return "Гілка 1" if x < LEFT_BOUND else ("Гілка 2" if x <= RIGHT_BOUND else "Гілка 3")


def reciprocal_exceeds_one(x: float) -> bool:
    """
    Перевіряє нерівність 1/x > 1 з використанням короткої схеми обчислення.
    Якщо x == 0, перший операнд кон'юнкції хибний, і ділення 1/x не виконується,
    тому ZeroDivisionError не виникає.
    """
    return x != 0.0 and 1.0 / x > 1.0


def main() -> None:
    """Демонстрація розгалужених обчислень на контрольних точках."""
    print("=" * 72)
    print(f"{'ВАРІАНТ 2. КУСОЧНО-НЕПЕРЕРВНА ФУНКЦІЯ: РОЗГАЛУЖЕННЯ':^72}")
    print("=" * 72)

    # Контрольні точки: усередині гілок та по обидва боки від меж -1 і 1
    control_points = [-3.0, -1.5, -1.0001, -1.0, 0.0, 0.5, 1.0, 1.0001, 2.0, 3.0]

    print(f"| {'x':^10} | {'Гілка':^10} | {'f(x)':^16} |")
    print("-" * 72)
    for x in control_points:
        y = evaluate_piecewise_function(x)
        print(f"| {x:^10.4f} | {classify_branch(x):^10} | {y:^16.8f} |")
    print("-" * 72)

    # Розриви на межах гілок: різниця між односторонньою границею та значенням у точці
    # x = -1: границя зліва дорівнює cos(1) + 1, значення f(-1) = -3
    left_limit_m1 = math.cos(1.0) + 1.0
    jump_m1 = left_limit_m1 - evaluate_piecewise_function(-1.0)
    # x = 1: значення f(1) = 3, границя справа дорівнює cbrt(0) = 0
    right_limit_p1 = 0.0
    jump_p1 = right_limit_p1 - evaluate_piecewise_function(1.0)
    print(f"Розрив у точці x = -1: границя зліва - значення = {jump_m1:+.6f}")
    print(f"Розрив у точці x = +1: границя справа - значення = {jump_p1:+.6f}")
    print("Функція кусочно-неперервна: у точках x = -1 та x = 1 має розриви першого роду.")

    # Коротка схема обчислення
    print("\nКоротка схема обчислення (1/x > 1):")
    for x in (0.0, 0.5, 2.0):
        print(f"  x = {x:4.1f}  ->  {reciprocal_exceeds_one(x)}")
    print("=" * 72)


if __name__ == "__main__":
    t_start = time.perf_counter()
    main()
    elapsed = time.perf_counter() - t_start
    print(f"Час виконання модуля розгалужень: {elapsed * 1000:.3f} мс\n")
