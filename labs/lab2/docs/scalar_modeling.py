"""
Лабораторна робота № 2. Модуль 1 (Варіант 2).
Аналітичне моделювання нелінійної функції двох змінних та розрахунок комплексного імпедансу.
Освітній компонент: Програмування на Python.
"""

import math
import cmath
import sys


def compute_variant_function(x: float, y: float) -> float:
    """
    Обчислює значення функції f(x, y) за формулою Варіанта 2:
    f(x, y) = ln(x^2 + 2) / (cos(y - x) + 1.5) + cbrt(x * e^y)
    """
    # 1. Чисельник першого доданка: ln(x^2 + 2)
    numerator = math.log(x**2 + 2.0)

    # 2. Знаменник першого доданка: cos(y - x) + 1.5
    # Оскільки cos(y - x) належить [-1; 1], знаменник завжди >= 0.5 > 0
    denominator = math.cos(y - x) + 1.5
    first_term = numerator / denominator

    # 3. Другий доданок: кубічний корінь з (x * e^y)
    radicand = x * math.exp(y)
    
    # Використовуємо math.cbrt (Python 3.11+) або універсальний розрахунок для дійсних чисел
    if hasattr(math, "cbrt"):
        second_term = math.cbrt(radicand)
    else:
        second_term = math.copysign(abs(radicand) ** (1.0 / 3.0), radicand)

    return first_term + second_term


def compute_rlc_impedance(r_resistance: float, l_inductance: float, c_capacitance: float, frequency_hz: float) -> complex:
    """
    Обчислює комплексний опір (імпеданс) послідовного RLC-контуру:
    Z = R + j * (omega * L - 1 / (omega * C)), де omega = 2 * pi * f
    """
    if frequency_hz <= 0.0 or c_capacitance <= 0.0 or l_inductance <= 0.0:
        raise ValueError("Параметри L, C та частота f повинні бути строго додатними.")

    omega = 2.0 * math.pi * frequency_hz
    reactance_l = omega * l_inductance
    reactance_c = 1.0 / (omega * c_capacitance)
    total_reactance = reactance_l - reactance_c

    return complex(r_resistance, total_reactance)


def main() -> None:
    """Головна точка входу для демонстрації аналітичних скалярних обчислень."""
    print("=" * 80)
    print(f"{'ВАРІАНТ 2: АНАЛІТИЧНЕ МОДЕЛЮВАННЯ ТА СКАЛЯРНІ ДАНІ':^80}")
    print("=" * 80)

    # 1. Розрахунок аналітичної функції f(x, y)
    test_x = 2.0
    test_y = 1.0
    result_val = compute_variant_function(test_x, test_y)

    # Еталонне значення для перевірки точності
    ref_first = math.log(test_x**2 + 2.0) / (math.cos(test_y - test_x) + 1.5)
    ref_arg = test_x * math.exp(test_y)
    ref_second = math.copysign(abs(ref_arg) ** (1.0 / 3.0), ref_arg)
    reference_val = ref_first + ref_second

    is_accurate = math.isclose(result_val, reference_val, rel_tol=1e-9, abs_tol=1e-12)

    print(f"Вхідні змінні:                  x = {test_x:.4f}, y = {test_y:.4f}")
    print(f"Формула:                        f(x, y) = ln(x^2+2)/(cos(y-x)+1.5) + cbrt(x*e^y)")
    print(f"Розраховане значення f(x, y):   {result_val:12.8f}")
    print(f"Еталонне значення верифікації:  {reference_val:12.8f}")
    print(f"Точність IEEE 754 (isclose):    {str(is_accurate).upper()} (rel_tol=1e-9)")
    print("-" * 80)

    # 2. Розрахунок комплексного імпедансу RLC контуру
    r_val = 120.0       # Ом
    l_val = 0.04        # Гн (40 мГн)
    c_val = 8.0e-6      # Ф (8 мкФ)
    freq_val = 250.0    # Гц

    z_complex = compute_rlc_impedance(r_val, l_val, c_val, freq_val)
    z_magnitude, z_phase_rad = cmath.polar(z_complex)
    z_phase_deg = math.degrees(z_phase_rad)

    print(f"{'РОЗРАХУНОК КОМПЛЕКСНОГО ІМПЕДАНСУ RLC-КОНТУРУ':^80}")
    print("-" * 80)
    print(f"Параметри: R = {r_val:.1f} Ом, L = {l_val * 1e3:.1f} мГн, C = {c_val * 1e6:.1f} мкФ, f = {freq_val:.1f} Гц")
    print(f"Комплексний імпеданс Z:         {z_complex.real:8.3f} + {z_complex.imag:8.3f}j Ом")
    print(f"Активний опір Re(Z):            {z_complex.real:8.3f} Ом")
    print(f"Реактивний опір Im(Z):          {z_complex.imag:8.3f} Ом")
    print(f"Повний модуль імпедансу |Z|:    {z_magnitude:8.3f} Ом")
    print(f"Фазовий зсув (Arg Z):           {z_phase_deg:8.3f} град ({z_phase_rad:8.4f} рад)")
    print("=" * 80)


if __name__ == "__main__":
    main()