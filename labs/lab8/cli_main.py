"""
Головна точка входу консольної утиліти empty_dir_cleaner (варіант 2).
Ручний розбір параметрів командного рядка sys.argv, пошук порожніх директорій
та їхнє безпечне видалення з режимом імітації --dry-run.

Коди завершення процесу:
    0 - успіх; 1 - помилка синтаксису аргументів; 2 - некоректний або небезпечний шлях;
    3 - критичний збій; 4 - частина директорій не вдалося видалити.
Освітній компонент: Програмування на Python.
"""

import sys
import time
from pathlib import Path

# Імпорт публічного інтерфейсу власного пакета fs_toolkit
from fs_toolkit import find_empty_directories, remove_empty_directories, print_cleanup_report


def print_usage_help() -> None:
    """Виводить інструкцію з використання утиліти командного рядка."""
    usage_text = """
empty_dir_cleaner - детектор порожніх папок з режимом імітації видалення.

ВИКОРИСТАННЯ:
    python cli_main.py --path <каталог> [--dry-run]

ПАРАМЕТРИ:
    --path <каталог> : (Обов'язковий) Шлях до каталогу, у якому шукаються порожні директорії.
    --dry-run        : (Опціональний) Режим імітації: знайдені каталоги лише показуються,
                       але не видаляються. Без цього прапорця каталоги ВИДАЛЯЮТЬСЯ.
    --help, -h       : Виведення цієї інформаційної довідки.

ПРИКЛАДИ:
    python cli_main.py --path ./test_sandbox --dry-run
    python cli_main.py --path ./test_sandbox

КОДИ ЗАВЕРШЕННЯ:
    0 - успіх, 1 - помилка аргументів, 2 - некоректний шлях, 3 - збій, 4 - помилки видалення
"""
    print(usage_text)


def parse_cli_arguments(args_list: list[str]) -> dict:
    """
    Здійснює ручний розбір списку аргументів sys.argv без сторонніх бібліотек.
    Елемент args_list[0] - ім'я скрипта, тому аналіз починається з індексу 1.
    Повертає словник конфігурації {"path": Path, "dry_run": bool}.
    """
    config = {"path": None, "dry_run": False}

    if "--help" in args_list or "-h" in args_list or len(args_list) <= 1:
        print_usage_help()
        sys.exit(0)

    i = 1
    while i < len(args_list):
        arg = args_list[i]

        if arg == "--path":
            # Значення відсутнє або замість нього йде інший прапорець
            if i + 1 >= len(args_list) or args_list[i + 1].startswith("--"):
                print("Помилка синтаксису: Після прапорця '--path' необхідно вказати шлях до каталогу.")
                sys.exit(1)
            config["path"] = Path(args_list[i + 1]).expanduser().resolve()
            i += 2

        elif arg == "--dry-run":
            config["dry_run"] = True            # прапорець без значення
            i += 1

        else:
            print(f"Помилка: Невідомий параметр командного рядка '{arg}'.")
            print_usage_help()
            sys.exit(1)

    if config["path"] is None:
        print("Помилка: Обов'язковий параметр '--path' не вказано.")
        print_usage_help()
        sys.exit(1)

    return config


def main() -> None:
    """Головна функція диспетчеризації CLI-утиліти."""
    # 1. Розбір вхідних параметрів командного рядка
    cli_config = parse_cli_arguments(sys.argv)
    target_directory: Path = cli_config["path"]
    dry_run: bool = cli_config["dry_run"]

    # 2. Захист: реальне видалення в кореневому або домашньому каталозі заборонено
    if not dry_run and (target_directory.parent == target_directory or target_directory == Path.home()):
        print(f"Помилка безпеки: реальне видалення в '{target_directory}' заборонено. "
              f"Вкажіть вкладений каталог або використайте --dry-run.")
        sys.exit(2)

    t_start = time.perf_counter()

    # 3. Пошук порожніх директорій і (за потреби) їхнє видалення
    try:
        scan_result = find_empty_directories(target_directory)
        actions = remove_empty_directories(scan_result["empty_dirs"], dry_run=dry_run)
    except ValueError as val_err:
        print(f"Помилка аргументів: {val_err}")
        sys.exit(2)
    except Exception as general_err:
        print(f"Критичний збій виконання: {general_err}")
        sys.exit(3)

    # 4. Формування звіту
    print_cleanup_report(scan_result, actions, str(target_directory), dry_run)

    t_elapsed = time.perf_counter() - t_start
    has_failures = any(a["status"] == "ПОМИЛКА" for a in actions)
    print(f"Операцію завершено за {t_elapsed * 1000:.3f} мс. Код завершення: {4 if has_failures else 0}.")
    sys.exit(4 if has_failures else 0)


if __name__ == "__main__":
    main()
