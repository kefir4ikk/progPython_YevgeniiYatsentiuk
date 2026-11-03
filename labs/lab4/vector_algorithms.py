"""
Лабораторна робота № 4. Модуль 1. Варіант 2.
Обробка одновимірного вектора: генерація, вилучення елементів, кратних 5,
пошук екстремумів та ручна реалізація бульбашкового сортування (Bubble Sort).
Конфігурація передається у вигляді незмінного кортежу.
Освітній компонент: Програмування на Python.
"""

import random
import time

# Незмінний конфігураційний кортеж параметрів (варіант 2):
# CONFIG = (N, M, K, X_MIN, X_MAX)
#   N     - довжина вектора V
#   M, K  - розмірність матриці A (використовуються в matrix_operations.py)
#   X_MIN, X_MAX - межі генерації випадкових цілих чисел
CONFIG: tuple[int, int, int, int, int] = (20, 3, 5, 0, 100)


def generate_random_vector(length: int, min_val: int, max_val: int) -> list[int]:
    """Генерує вектор випадкових цілих чисел довжини length у діапазоні [min_val, max_val]."""
    if length <= 0:
        raise ValueError("Довжина вектора повинна бути строго додатною.")
    if min_val > max_val:
        raise ValueError("Нижня межа діапазону не може перевищувати верхню.")

    return [random.randint(min_val, max_val) for _ in range(length)]


def remove_multiples_of(vector: list[int], divisor: int) -> list[int]:
    """
    Вилучає з вектора усі елементи, кратні divisor (List Comprehension).
    Нуль кратний будь-якому числу, тому також вилучається.
    """
    if divisor == 0:
        raise ValueError("Дільник не може дорівнювати нулю.")

    return [x for x in vector if x % divisor != 0]


def find_extremes(vector: list[int]) -> tuple[int, int, int, int]:
    """
    Знаходить мінімум і максимум вектора разом з індексами першого входження.
    Повертає кортеж (min_value, min_index, max_value, max_index).
    Реалізовано одним проходом за O(N) без вбудованих min()/max().
    """
    if not vector:
        raise ValueError("Неможливо знайти екстремуми порожнього вектора.")

    min_idx = max_idx = 0
    for i in range(1, len(vector)):
        if vector[i] < vector[min_idx]:
            min_idx = i
        if vector[i] > vector[max_idx]:
            max_idx = i

    return vector[min_idx], min_idx, vector[max_idx], max_idx


def bubble_sort_manual(input_list: list[int]) -> tuple[list[int], int, int]:
    """
    Бульбашкове сортування (Bubble Sort) за зростанням, без .sort() і sorted().
    Працює з копією, тому вхідний список не змінюється.
    Містить оптимізацію раннього виходу: якщо за прохід не було жодного обміну,
    масив уже впорядкований.
    Повертає кортеж (відсортований_список, кількість_порівнянь, кількість_обмінів).
    Часова складність: O(N^2) у середньому та найгіршому, O(N) у найкращому випадку.
    """
    arr = list(input_list)
    n = len(arr)
    comparisons = 0
    swaps = 0

    for i in range(n - 1):
        swapped = False
        # Після i проходів останні i елементів уже стоять на своїх місцях
        for j in range(n - 1 - i):
            comparisons += 1
            if arr[j] > arr[j + 1]:
                # Паралельний обмін через кортежне розпакування
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swaps += 1
                swapped = True
        if not swapped:
            break

    return arr, comparisons, swaps


def main() -> None:
    """Головна функція демонстрації обробки вектора (варіант 2)."""
    # Паралельне розпакування конфігураційного кортежу
    n, m, k, x_min, x_max = CONFIG

    # Фіксоване зерно для повторюваності результатів
    random.seed(42)
    raw_vector = generate_random_vector(n, x_min, x_max)

    print("=" * 80)
    print(f"{'ВАРІАНТ 2. ОБРОБКА ВЕКТОРА ТА БУЛЬБАШКОВЕ СОРТУВАННЯ':^80}")
    print("=" * 80)
    print(f"CONFIG (розпакований tuple): N = {n}, M = {m}, K = {k}, "
          f"діапазон = [{x_min}, {x_max}]")
    print(f"Початковий вектор V ({len(raw_vector)} ел.):")
    print(f"  {raw_vector}")

    # 1. Вилучення елементів, кратних 5
    filtered = remove_multiples_of(raw_vector, 5)
    removed = [x for x in raw_vector if x % 5 == 0]
    print(f"\nВилучені елементи, кратні 5 ({len(removed)} шт.): {removed}")
    print(f"Вектор після вилучення ({len(filtered)} ел.):")
    print(f"  {filtered}")

    # 2. Екстремуми відфільтрованого вектора
    if filtered:
        v_min, i_min, v_max, i_max = find_extremes(filtered)
        print(f"\nМінімум: {v_min} (індекс {i_min}), максимум: {v_max} (індекс {i_max})")
    else:
        print("\nПісля фільтрації вектор порожній, екстремумів немає.")

    # 3. Бульбашкове сортування (ручна реалізація)
    t_start = time.perf_counter()
    sorted_manual, cmp_count, swap_count = bubble_sort_manual(filtered)
    t_bubble = time.perf_counter() - t_start
    print(f"\nBubble Sort за зростанням:")
    print(f"  {sorted_manual}")
    print(f"Порівнянь: {cmp_count}, обмінів: {swap_count}, час: {t_bubble * 1000:.4f} мс")

    # 4. Верифікація зі стандартним Timsort
    t_start = time.perf_counter()
    sorted_builtin = sorted(filtered)
    t_timsort = time.perf_counter() - t_start
    print(f"\nTimsort (sorted): час {t_timsort * 1000:.4f} мс")
    print(f"Результати співпадають: {sorted_manual == sorted_builtin}")

    # 5. Перевірка, що вихідний вектор не було змінено
    print(f"Вихідний вектор V не змінено: {len(raw_vector) == n}")
    print("=" * 80)


if __name__ == "__main__":
    t_total = time.perf_counter()
    main()
    elapsed = time.perf_counter() - t_total
    print(f"Час виконання модуля векторних алгоритмів: {elapsed * 1000:.4f} мс\n")
