"""
Лабораторна робота № 5. Модуль 2. Варіант 2.
Синтаксичний розбір системного журналу Linux Syslog регулярними виразами
з іменованими групами, валідація полів, групування за демоном (Daemon_Name)
та формування табличного звіту через f-strings.

Формат кадру:
    Mon DD HH:MM:SS hostname daemon[PID]: SEVERITY: message
Приклад:
    Sep  2 08:14:21 srv-web01 sshd[1034]: ERR: Failed password for root
Освітній компонент: Програмування на Python.
"""

import re
import time
from pathlib import Path

from text_sanitizer import sanitize_log_line

# Скомпільований регулярний вираз з іменованими групами (режим VERBOSE дозволяє коментарі)
LOG_PATTERN = re.compile(
    r"""
    ^(?P<month>[A-Z][a-z]{2})\s+          # місяць: три літери (Sep)
    (?P<day>\d{1,2})\s+                   # день місяця: 1-2 цифри
    (?P<time>\d{2}:\d{2}:\d{2})\s+        # час HH:MM:SS
    (?P<hostname>[A-Za-z0-9][A-Za-z0-9.\-]*)\s+   # ім'я хоста
    (?P<daemon>[A-Za-z0-9_.\-/]+)         # назва демона
    \[(?P<pid>\d+)\]:\s+                  # PID у квадратних дужках
    (?P<severity>INFO|ERR):\s+            # рівень важливості
    (?P<message>.+)$                      # текст повідомлення до кінця рядка
    """,
    re.VERBOSE,
)

# Максимальна кількість днів у місяці (лютий беремо з урахуванням високосного року)
MONTH_DAYS: dict[str, int] = {
    "Jan": 31, "Feb": 29, "Mar": 31, "Apr": 30, "May": 31, "Jun": 30,
    "Jul": 31, "Aug": 31, "Sep": 30, "Oct": 31, "Nov": 30, "Dec": 31,
}
PID_MAX: int = 4_194_304   # типове значення kernel.pid_max для 64-бітних систем

REPORT_WIDTH: int = 88


def validate_record(record: dict) -> str | None:
    """
    Семантична валідація вилучених полів.
    Повертає текст причини відхилення або None, якщо запис коректний.
    """
    month, day = record["month"], int(record["day"])
    if month not in MONTH_DAYS:
        return f"невідомий місяць '{month}'"
    if not 1 <= day <= MONTH_DAYS[month]:
        return f"день {day} поза діапазоном для {month}"

    hours, minutes, seconds = (int(part) for part in record["time"].split(":"))
    if hours > 23 or minutes > 59 or seconds > 59:
        return f"некоректний час {record['time']}"

    if not 1 <= int(record["pid"]) <= PID_MAX:
        return f"PID {record['pid']} поза діапазоном 1..{PID_MAX}"
    return None


def parse_syslog_file(file_path: Path) -> tuple[list[dict], list[tuple[int, str, str]]]:
    """
    Зчитує журнал і повертає кортеж (коректні_записи, відхилені_рядки).
    Відхилений рядок - це кортеж (номер_рядка, причина, нормалізований_текст).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Вхідний файл журналу '{file_path}' не знайдено.")

    records: list[dict] = []
    rejected: list[tuple[int, str, str]] = []

    with open(file_path, mode="r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            normalized = sanitize_log_line(line)
            if not normalized or normalized.startswith("#"):
                continue  # порожні рядки та коментарі

            match = LOG_PATTERN.search(normalized)
            if match is None:
                rejected.append((line_num, "не відповідає формату кадру", normalized))
                continue

            record = match.groupdict()
            reason = validate_record(record)
            if reason is not None:
                rejected.append((line_num, reason, normalized))
                continue

            record["day"] = int(record["day"])
            record["pid"] = int(record["pid"])
            record["line_num"] = line_num
            records.append(record)

    return records, rejected


def group_by_daemon(records: list[dict]) -> dict[str, dict]:
    """
    Групує записи за назвою демона. Для кожного демона підраховує
    загальну кількість подій, INFO, ERR та множину PID із помилками.
    """
    groups: dict[str, dict] = {}
    for rec in records:
        g = groups.setdefault(rec["daemon"], {"total": 0, "info": 0, "err": 0, "err_pids": set()})
        g["total"] += 1
        if rec["severity"] == "ERR":
            g["err"] += 1
            g["err_pids"].add(rec["pid"])
        else:
            g["info"] += 1
    return groups


def shorten(text: str, width: int) -> str:
    """Обрізає текст до width символів, додаючи символ «…» при скороченні."""
    return text if len(text) <= width else text[: width - 1] + "…"


def print_records_table(records: list[dict]) -> None:
    """Виводить таблицю коректно розібраних записів."""
    print("=" * REPORT_WIDTH)
    print(f"{'ЗВІТ ПРО РОЗБІР ЖУРНАЛУ LINUX SYSLOG':^{REPORT_WIDTH}}")
    print("=" * REPORT_WIDTH)
    print(f"| {'Час':^15} | {'Хост':^10} | {'Процес[PID]':^14} | {'Рівень':^6} | {'Повідомлення':^27} |")
    print("-" * REPORT_WIDTH)
    for rec in records:
        stamp = f"{rec['month']} {rec['day']:>2d} {rec['time']}"
        proc = f"{rec['daemon']}[{rec['pid']}]"
        print(
            f"| {stamp:<15} | {rec['hostname']:<10} | {proc:<14} | {rec['severity']:^6} | "
            f"{shorten(rec['message'], 27):<27} |"
        )
    print("=" * REPORT_WIDTH)


def print_group_table(groups: dict[str, dict]) -> None:
    """Виводить таблицю групування за Daemon_Name, відсортовану за кількістю помилок."""
    print(f"\n{'ГРУПУВАННЯ ПОДІЙ ЗА ДЕМОНОМ (Daemon_Name)':^{REPORT_WIDTH}}")
    print("-" * REPORT_WIDTH)
    print(f"| {'Демон':^12} | {'Всього':^6} | {'INFO':^5} | {'ERR':^5} | {'% ERR':^7} | {'PID із помилками':^34} |")
    print("-" * REPORT_WIDTH)
    ordered = sorted(groups.items(), key=lambda item: (-item[1]["err"], item[0]))
    for daemon, g in ordered:
        share = 100.0 * g["err"] / g["total"]
        pids = ", ".join(str(p) for p in sorted(g["err_pids"])) or "-"
        print(
            f"| {daemon:<12} | {g['total']:>6d} | {g['info']:>5d} | {g['err']:>5d} | "
            f"{share:>6.1f}% | {pids:<34} |"
        )
    print("-" * REPORT_WIDTH)


def print_rejected(rejected: list[tuple[int, str, str]]) -> None:
    """Виводить список відхилених рядків із причинами."""
    print(f"\n{'ВІДХИЛЕНІ РЯДКИ':^{REPORT_WIDTH}}")
    print("-" * REPORT_WIDTH)
    if not rejected:
        print("  Відхилених рядків немає.")
    for line_num, reason, text in rejected:
        print(f"  Рядок {line_num:>2d}: {reason}")
        print(f"            {shorten(text, REPORT_WIDTH - 12)}")
    print("-" * REPORT_WIDTH)


def print_summary(records: list[dict], rejected: list, groups: dict[str, dict]) -> None:
    """Виводить підсумкову агреговану статистику."""
    err_total = sum(g["err"] for g in groups.values())
    err_daemons = [name for name, g in groups.items() if g["err"] > 0]
    worst = max(groups.items(), key=lambda item: (item[1]["err"], item[0]))
    share = 100.0 * err_total / len(records) if records else 0.0

    print(f"\n{'ПІДСУМКОВА СТАТИСТИКА':^{REPORT_WIDTH}}")
    print("-" * REPORT_WIDTH)
    print(f"  Коректно розібрано записів:        {len(records):>4d}")
    print(f"  Відхилено рядків:                  {len(rejected):>4d}")
    print(f"  Унікальних демонів:                {len(groups):>4d}")
    print(f"  Подій рівня ERR:                   {err_total:>4d} ({share:.1f}% від усіх записів)")
    print(f"  Демонів, що мали помилки:          {len(err_daemons):>4d}")
    print(f"  Найбільше помилок у демона:        {worst[0]} ({worst[1]['err']})")
    print("=" * REPORT_WIDTH + "\n")


def main() -> None:
    """Головна точка входу модуля розбору журналу."""
    log_path = Path(__file__).with_name("input_logs.txt")

    t_start = time.perf_counter()
    records, rejected = parse_syslog_file(log_path)
    groups = group_by_daemon(records)

    print()
    print_records_table(records)
    print_group_table(groups)
    print_rejected(rejected)
    print_summary(records, rejected, groups)
    elapsed = time.perf_counter() - t_start

    print(f"Час виконання повного циклу аналізу тексту: {elapsed * 1000:.3f} мс\n")


if __name__ == "__main__":
    main()
