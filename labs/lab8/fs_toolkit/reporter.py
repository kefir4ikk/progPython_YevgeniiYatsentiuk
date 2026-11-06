"""
Модуль форматування та консольного виведення звіту про порожні директорії.
Освітній компонент: Програмування на Python.
"""

REPORT_WIDTH: int = 92


def _short_path(text: str, width: int) -> str:
    """Скорочує довгий шлях зліва, зберігаючи його кінець."""
    return text if len(text) <= width else "..." + text[-(width - 3):]


def print_cleanup_report(scan: dict, actions: list[dict], search_root: str, dry_run: bool) -> None:
    """Виводить таблицю знайдених порожніх каталогів і підсумкову статистику."""
    header_sep = "=" * REPORT_WIDTH
    row_sep = "-" * REPORT_WIDTH
    mode = "СИМУЛЯЦІЯ (--dry-run, змін не вносилось)" if dry_run else "РЕАЛЬНЕ ВИДАЛЕННЯ"

    print("\n" + header_sep)
    print(f"{'ЗВІТ ДЕТЕКТОРА ПОРОЖНІХ ДИРЕКТОРІЙ (empty_dir_cleaner)':^{REPORT_WIDTH}}")
    print(header_sep)
    print(f"Базова директорія пошуку: {search_root}")
    print(f"Режим роботи:             {mode}")
    print(row_sep)

    if actions:
        print(f"| {'№':^3} | {'Відносний шлях':<25} | {'Вміст':^12} | "
              f"{'Змінено':^16} | {'Права':^7} | {'Статус':^10} |")
        print(row_sep)
        for idx, act in enumerate(actions, start=1):
            rel = _short_path(act["relative_path"].as_posix(), 25)
            print(f"| {idx:^3d} | {rel:<25} | {act['kind']:^12} | "
                  f"{act['modified_at']:^16} | {act['permissions']:^7} | {act['status']:^10} |")
        print(header_sep)
    else:
        print(f"{'Порожніх директорій не виявлено.':^{REPORT_WIDTH}}")
        print(header_sep)

    total = len(actions)
    pure_empty = sum(1 for a in actions if a["kind"] == "порожня")
    only_subdirs = total - pure_empty
    removed = sum(1 for a in actions if a["status"] == "ВИДАЛЕНО")
    failed = [a for a in actions if a["status"] == "ПОМИЛКА"]

    print(f"{'ПІДСУМКОВА СТАТИСТИКА':^{REPORT_WIDTH}}")
    print(row_sep)
    print(f"  Проскановано директорій:                   {scan['dirs_scanned']:>5d}")
    print(f"  Файлів та інших об'єктів у піддереві:      {scan['objects_seen']:>5d}")
    print(f"  Знайдено порожніх директорій:              {total:>5d}")
    print(f"     з них повністю порожніх:                {pure_empty:>5d}")
    print(f"     з них лише з порожніми підкаталогами:   {only_subdirs:>5d}")
    max_depth = max((a["depth"] for a in actions), default=0)
    print(f"  Максимальна глибина порожнього каталогу:   {max_depth:>5d}")
    if dry_run:
        print(f"  Було б видалено (симуляція):               {total:>5d}")
    else:
        print(f"  Видалено:                                  {removed:>5d}")
        print(f"  Помилок видалення:                         {len(failed):>5d}")
    print(f"  Недоступних директорій (пропущено):        {len(scan['unreadable']):>5d}")
    if scan["root_is_empty"]:
        print("  Увага: сама базова директорія порожня, але вона не видаляється.")
    for act in failed:
        print(f"  Помилка: {act['relative_path'].as_posix()}: {act['error']}")
    for path, reason in scan["unreadable"]:
        print(f"  Недоступно: {path}: {reason}")
    print(header_sep + "\n")
