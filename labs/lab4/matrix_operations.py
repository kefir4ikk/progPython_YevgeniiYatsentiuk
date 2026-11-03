"""
Лабораторна робота № 4. Модуль 2. Варіант 2.
Матрична алгебра: генерація матриці A (3 x 5), множення на вектор-стовпець X,
пошук мінімуму кожного рядка та пошук сідлових точок.
Освітній компонент: Програмування на Python.
"""

import random
import time

# Незмінний конфігураційний кортеж параметрів (варіант 2):
# CONFIG = (N, M, K, X_MIN, X_MAX)
CONFIG: tuple[int, int, int, int, int] = (20, 3, 5, 0, 100)


def generate_matrix(rows: int, cols: int, min_val: int, max_val: int) -> list[list[int]]:
    """Генерує матрицю rows x cols вкладеними генераторами списків."""
    if rows <= 0 or cols <= 0:
        raise ValueError("Кількість рядків і стовпців повинна бути строго додатною.")
    if min_val > max_val:
        raise ValueError("Нижня межа діапазону не може перевищувати верхню.")

    # Кожен рядок створюється окремо, тому спільного стану між рядками немає
    return [[random.randint(min_val, max_val) for _ in range(cols)] for _ in range(rows)]


def generate_column_vector(length: int, min_val: int, max_val: int) -> list[list[int]]:
    """Генерує вектор-стовпець X розмірності length x 1 у вигляді списку одноелементних рядків."""
    return generate_matrix(length, 1, min_val, max_val)


def multiply_matrices(matrix_a: list[list[int]], matrix_b: list[list[int]]) -> list[list[int]]:
    """
    Обчислює матричний добуток C = A x B за формулою C[i][j] = sum(A[i][k] * B[k][j]).
    Кількість стовпців A повинна дорівнювати кількості рядків B, інакше - ValueError.
    Складність: O(m * n * p).
    """
    rows_a, cols_a = len(matrix_a), len(matrix_a[0])
    rows_b, cols_b = len(matrix_b), len(matrix_b[0])

    if cols_a != rows_b:
        raise ValueError(
            f"Несумісні розмірності для множення: A({rows_a}x{cols_a}) та B({rows_b}x{cols_b})."
        )

    return [
        [sum(matrix_a[i][k] * matrix_b[k][j] for k in range(cols_a)) for j in range(cols_b)]
        for i in range(rows_a)
    ]


def row_minima(matrix: list[list[int]]) -> list[tuple[int, int, int]]:
    """
    Знаходить мінімум кожного рядка матриці.
    Повертає список кортежів (індекс_рядка, індекс_стовпця_мінімуму, значення).
    """
    result = []
    for i, row in enumerate(matrix):
        min_j = 0
        for j in range(1, len(row)):
            if row[j] < row[min_j]:
                min_j = j
        result.append((i, min_j, row[min_j]))
    return result


def find_saddle_points(matrix: list[list[int]]) -> list[tuple[int, int, int]]:
    """
    Знаходить усі сідлові точки: елементи, що є мінімальними у своєму рядку
    та одночасно максимальними у своєму стовпці.
    Повертає список кортежів (індекс_рядка, індекс_стовпця, значення).
    """
    rows, cols = len(matrix), len(matrix[0])

    minima = [min(row) for row in matrix]
    maxima = [max(matrix[r][c] for r in range(rows)) for c in range(cols)]

    return [
        (i, j, matrix[i][j])
        for i in range(rows)
        for j in range(cols)
        if matrix[i][j] == minima[i] and matrix[i][j] == maxima[j]
    ]


def print_matrix(matrix: list[list[int]], title: str) -> None:
    """Виводить матрицю у вигляді вирівняної таблиці."""
    print(f"\n--- {title} ({len(matrix)}x{len(matrix[0])}) ---")
    for row in matrix:
        print("  [ " + " ".join(f"{elem:6d}" for elem in row) + " ]")


def print_saddles(saddles: list[tuple[int, int, int]]) -> None:
    """Виводить результат пошуку сідлових точок."""
    if not saddles:
        print("  Сідлових точок не виявлено.")
        return
    for idx, (r, c, v) in enumerate(saddles, start=1):
        print(f"  Точка {idx}: рядок = {r}, стовпець = {c}, значення = {v}")


def main() -> None:
    """Головна функція демонстрації матричних операцій (варіант 2)."""
    n, m, k, x_min, x_max = CONFIG  # паралельне розпакування кортежу

    random.seed(101)

    print("=" * 80)
    print(f"{'ВАРІАНТ 2. МАТРИЦЯ 3x5, ДОБУТОК A x X ТА СІДЛОВІ ТОЧКИ':^80}")
    print("=" * 80)
    print(f"CONFIG: M = {m}, K = {k}, діапазон елементів = [{x_min}, {x_max}]")

    # 1. Матриця A (M x K) і вектор-стовпець X (K x 1)
    mat_a = generate_matrix(m, k, x_min, x_max)
    vec_x = generate_column_vector(k, x_min, x_max)
    print_matrix(mat_a, "Матриця A")
    print_matrix(vec_x, "Вектор-стовпець X")

    # 2. Y = A x X
    vec_y = multiply_matrices(mat_a, vec_x)
    print_matrix(vec_y, "Вектор Y = A x X")

    # Контрольна перевірка першого елемента вручну
    terms = " + ".join(f"{mat_a[0][t]}*{vec_x[t][0]}" for t in range(k))
    manual_y0 = sum(mat_a[0][t] * vec_x[t][0] for t in range(k))
    print(f"\nПеревірка Y[0] = {terms} = {manual_y0}  ->  збігається: {manual_y0 == vec_y[0][0]}")

    # 3. Мінімум кожного рядка матриці A
    print("\nМінімум кожного рядка матриці A:")
    for i, j, v in row_minima(mat_a):
        print(f"  Рядок {i}: min = {v} (стовпець {j})")

    # 4. Сідлові точки матриці A
    print("\nСідлові точки згенерованої матриці A:")
    print_saddles(find_saddle_points(mat_a))

    # 5. Контрольні матриці з відомим результатом
    control_1 = [
        [7, 8, 9],
        [4, 5, 6],
        [1, 2, 3],
    ]
    control_2 = [
        [5, 5, 6],
        [5, 5, 7],
        [1, 2, 8],
    ]
    print_matrix(control_1, "Контрольна матриця M1")
    print("Сідлові точки M1 (очікується одна: (0, 0) = 7):")
    print_saddles(find_saddle_points(control_1))

    print_matrix(control_2, "Контрольна матриця M2")
    print("Сідлові точки M2 (очікується чотири, усі зі значенням 5):")
    print_saddles(find_saddle_points(control_2))

    # 6. Перевірка контролю розмірностей
    print("\nПеревірка контролю розмірностей (A 3x5 на матрицю 4x1):")
    try:
        multiply_matrices(mat_a, [[1], [2], [3], [4]])
    except ValueError as err:
        print(f"  Перехоплено ValueError: {err}")

    print("=" * 80)


if __name__ == "__main__":
    t_start = time.perf_counter()
    main()
    elapsed = time.perf_counter() - t_start
    print(f"Час виконання модуля матричної алгебри: {elapsed * 1000:.4f} мс\n")
