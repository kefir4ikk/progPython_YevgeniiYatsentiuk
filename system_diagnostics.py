"""
Модуль системної діагностики інженерного середовища Python.
Освітній компонент: Програмування на Python.
Спеціальність: F7 Комп'ютерна інженерія.
"""

import os
import platform
import sys
import time


def collect_environment_metadata() -> dict:
    """
    Здійснює агрегацію характеристик апаратної платформи,
    операційної системи та параметрів інтерпретатора CPython.
    """
    # Збір інформації про версію та архітектуру платформи
    system_info = {
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_architecture": platform.architecture()[0],
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_compiler": platform.python_compiler(),
        "byte_order": sys.byteorder,
        "interpreter_path": sys.executable,
        "active_conda_env": os.environ.get("CONDA_DEFAULT_ENV", "None (Global/Non-Conda)"),
        "recursion_limit": sys.getrecursionlimit(),
        "thread_switch_interval": sys.getswitchinterval(),
    }
    return system_info


def calculate_memory_footprint() -> dict:
    """
    Обчислює фізичний розмір базових скалярних та складених
    структур даних у байтах за допомогою функції sys.getsizeof.
    """
    # Створення тестових екземплярів різних типів даних
    sample_int_zero = 0
    sample_int_large = 2**64
    sample_float = 3.141592653589793
    sample_complex = 1.0 + 2.0j
    sample_bool = True
    sample_none = None
    sample_str_empty = ""
    sample_str_ascii = "Computer Engineering"
    sample_list_empty = []
    sample_tuple_empty = ()
    sample_dict_empty = {}
    sample_set_empty = set()

    # Формування словника розмірів об'єктів у байтах
    sizes = {
        "int (0)": sys.getsizeof(sample_int_zero),
        "int (2^64)": sys.getsizeof(sample_int_large),
        "float": sys.getsizeof(sample_float),
        "complex": sys.getsizeof(sample_complex),
        "bool": sys.getsizeof(sample_bool),
        "NoneType": sys.getsizeof(sample_none),
        "str (empty)": sys.getsizeof(sample_str_empty),
        "str (ASCII, len=20)": sys.getsizeof(sample_str_ascii),
        "list (empty)": sys.getsizeof(sample_list_empty),
        "tuple (empty)": sys.getsizeof(sample_tuple_empty),
        "dict (empty)": sys.getsizeof(sample_dict_empty),
        "set (empty)": sys.getsizeof(sample_set_empty),
    }
    return sizes


def verify_integer_cache() -> list:
    """
    Здійснює експериментальну верифікацію роботи механізму
    Small Integer Cache для інтервалу [-5, 256] та чисел поза ним.
    """
    cache_results = []
    test_integers = [-5, 0, 100, 256, 257, 1000]

    for val in test_integers:
        # Створення двох незалежних змінних через обчислення
        int_a = int(str(val))
        int_b = int(str(val))
        is_identical = int_a is int_b
        cache_results.append(
            {
                "value": val,
                "id_a": id(int_a),
                "id_b": id(int_b),
                "is_same_object": is_identical,
            }
        )
    return cache_results


def print_formatted_report() -> None:
    """
    Виводить на екран консолі комплексну діагностичну таблицю
    з використанням сучасних специфікаторів форматування f-strings.
    """
    meta = collect_environment_metadata()
    memory = calculate_memory_footprint()
    cache_data = verify_integer_cache()

    separator = "=" * 80
    sub_separator = "-" * 80

    print(separator)
    print(f"{'ЗВІТ СИСТЕМНОЇ ДІАГНОСТИКИ СЕРЕДОВИЩА PYTHON':^80}")
    print(separator)

    # Виведення метаданих платформи
    print(f"Операційна система:      {meta['os_name']} {meta['os_release']} ({meta['os_architecture']})")
    print(f"Апаратний процесор:      {meta['processor']}")
    print(f"Версія інтерпретатора:   {meta['python_version']} ({meta['python_implementation']})")
    print(f"Компілятор ядра CPython: {meta['python_compiler']}")
    print(f"Порядок байтів системи:  {meta['byte_order'].upper()}-ENDIAN")
    print(f"Активоване Conda-env:    {meta['active_conda_env']}")
    print(f"Шлях до інтерпретатора:  {meta['interpreter_path']}")
    print(f"Ліміт глибини рекурсії:  {meta['recursion_limit']} кадрів")
    print(f"Квант перемикання GIL:   {meta['thread_switch_interval']} с")

    print(sub_separator)
    print(f"{'ПРОСТОРОВІ НАКЛАДНІ ВИТРАТИ СТРУКТУР ДАНИХ (CPython 64-bit)':^80}")
    print(sub_separator)
    print(f"| {'Тип даних та стан':<30} | {'Розмір у пам`яті (Байти)':<43} |")
    print(sub_separator)
    for type_name, size_bytes in memory.items():
        print(f"| {type_name:<30} | {size_bytes:<43} |")

    print(sub_separator)
    print(f"{'ВЕРИФІКАЦІЯ МЕХАНІЗМУ SMALL INTEGER CACHE':^80}")
    print(sub_separator)
    print(f"| {'Число':<8} | {'Адреса id(a)':<18} | {'Адреса id(b)':<18} | {'a is b':<12} | {'Статус пулу':<10} |")
    print(sub_separator)
    for row in cache_data:
        pool_status = "КЕШОВАНЕ" if row["is_same_object"] else "ДИНАМІЧНЕ"
        print(
            f"| {row['value']:<8} | {row['id_a']:<18} | {row['id_b']:<18} | {str(row['is_same_object']):<12} | {pool_status:<10} |"
        )
    print(separator)


if __name__ == "__main__":
    t_start = time.perf_counter()
    print_formatted_report()
    t_elapsed = time.perf_counter() - t_start
    print(f"Час повної діагностики середовища: {t_elapsed * 1000:.4f} мс\n")