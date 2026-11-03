"""
Лабораторна робота № 6. Модуль 2. Варіант 2.
Аудит прав користувачів Active Directory проти шаблону відділу (множини),
розрахунок коефіцієнта Жаккара та частотний аналіз входів засобами
collections.Counter.
Освітній компонент: Програмування на Python.
"""

import time
from collections import Counter

from network_inventory import create_initial_user_database

REPORT_WIDTH: int = 88

# Заголовки стовпців із зворотним слешем винесено за межі f-рядків (Python < 3.12 не допускає \ у виразах)
COL_EXCESS: str = "|A\\B|"
COL_MISSING: str = "|B\\A|"

# Нормативні шаблони ролей за відділом (Baseline). frozenset - незмінні множини
ROLE_TEMPLATES: dict[str, frozenset[str]] = {
    "IT": frozenset({"domain_users", "vpn_access", "remote_desktop",
                     "admin_console", "file_share_read", "monitoring_view"}),
    "Finance": frozenset({"domain_users", "file_share_read", "file_share_write",
                          "payroll_access", "erp_access"}),
    "HR": frozenset({"domain_users", "file_share_read", "hr_portal", "recruiting_tool"}),
    "Sales": frozenset({"domain_users", "file_share_read", "crm_access", "vpn_access"}),
}

# Потік успішних входів у домен (журнал автентифікації)
LOGIN_EVENTS: list[str] = [
        "kromanenko", "tmelnyk", "mpetrenko", "svc_backup2",
        "asmirnova", "ibondar", "svc_backup2", "mpetrenko",
        "asmirnova", "pkovalenko", "ibondar", "pkovalenko",
        "dshevchenko", "mpetrenko", "pkovalenko", "dshevchenko",
        "asmirnova", "pkovalenko", "asmirnova", "dshevchenko",
        "asmirnova", "nhavrylenko", "pkovalenko", "pkovalenko",
        "tmelnyk", "tmelnyk", "pkovalenko", "mpetrenko",
        "tmelnyk", "asmirnova", "asmirnova", "asmirnova",
        "mpetrenko", "nhavrylenko", "asmirnova",
]


def audit_user_roles(actual_roles: set[str], baseline_roles: frozenset[str]) -> dict:
    """
    Теоретико-множинний аудит ролей користувача відносно шаблону:
    надлишкові права A \\ B, відсутні обов'язкові права B \\ A, перетин A ∩ B
    та коефіцієнт Жаккара J(A, B) = |A ∩ B| / |A ∪ B|.
    """
    excess = actual_roles.difference(baseline_roles)
    missing = baseline_roles.difference(actual_roles)
    compliant = actual_roles.intersection(baseline_roles)
    union = actual_roles.union(baseline_roles)

    jaccard = len(compliant) / len(union) if union else 1.0

    return {
        "compliant": compliant,
        "excess": excess,
        "missing": missing,
        "jaccard": jaccard,
    }


def classify_status(user: dict, result: dict) -> str:
    """Визначає статус обліковки: КРИТИЧНО / НАДЛИШОК / НЕДОСТАТНЬО / OK."""
    if not user["is_active"] and user["roles"]:
        return "КРИТИЧНО"          # неактивний обліковий запис зберігає права доступу
    if result["excess"]:
        return "НАДЛИШОК"
    if result["missing"]:
        return "НЕДОСТАТНЬО"
    return "OK"


def audit_all_users(users_db: dict) -> dict[str, dict]:
    """
    Виконує аудит усіх користувачів. Для неактивних записів еталоном є порожня
    множина прав (порожній frozenset): будь-яка збережена роль є порушенням.
    """
    results = {}
    for username, user in users_db.items():
        baseline = ROLE_TEMPLATES[user["department"]] if user["is_active"] else frozenset()
        res = audit_user_roles(user["roles"], baseline)
        res["status"] = classify_status(user, res)
        res["baseline_size"] = len(baseline)
        results[username] = res
    return results


def analyze_login_frequency(events: list[str]) -> Counter:
    """Частотний аналіз потоку входів за допомогою collections.Counter."""
    return Counter(events)


def print_audit_table(users_db: dict, results: dict[str, dict]) -> None:
    """Виводить зведену таблицю аудиту та деталі порушень."""
    header = (f"| {'Користувач':<15} | {'Відділ':<8} | {'Статус':^12} | {'|A|':^4} | "
              f"{'|B|':^4} | {COL_EXCESS:^6} | {COL_MISSING:^6} | {'J(A,B)':^8} |")
    print("=" * REPORT_WIDTH)
    print(f"{'АУДИТ ПРАВ КОРИСТУВАЧІВ ПРОТИ ШАБЛОНУ ВІДДІЛУ':^{REPORT_WIDTH}}")
    print("=" * REPORT_WIDTH)
    print(header)
    print("-" * REPORT_WIDTH)
    for username in sorted(results):
        r, u = results[username], users_db[username]
        print(f"| {username:<15} | {u['department']:<8} | {r['status']:^12} | "
              f"{len(u['roles']):^4d} | {r['baseline_size']:^4d} | {len(r['excess']):^6d} | "
              f"{len(r['missing']):^6d} | {r['jaccard']:^8.4f} |")
    print("-" * REPORT_WIDTH)

    print(f"{'ДЕТАЛІ ПОРУШЕНЬ':^{REPORT_WIDTH}}")
    print("-" * REPORT_WIDTH)
    for username in sorted(results):
        r = results[username]
        if r["status"] == "OK":
            continue
        print(f"  {username} [{r['status']}]")
        if r["excess"]:
            print(f"      Надлишкові права (A \\ B): {', '.join(sorted(r['excess']))}")
        if r["missing"]:
            print(f"      Відсутні права   (B \\ A): {', '.join(sorted(r['missing']))}")
    print("-" * REPORT_WIDTH)


def print_login_analysis(users_db: dict, events: list[str]) -> None:
    """Виводить частотний аналіз входів та пов'язані множинні перевірки."""
    freq = analyze_login_frequency(events)
    total = len(events)

    print(f"{'ЧАСТОТНИЙ АНАЛІЗ ВХОДІВ (TOP-3)':^{REPORT_WIDTH}}")
    print("-" * REPORT_WIDTH)
    print(f"| {'Ранг':^8} | {'Користувач':^26} | {'Кількість входів':^21} | {'Частка від усіх':^20} |")
    print("-" * REPORT_WIDTH)
    for rank, (name, count) in enumerate(freq.most_common(3), start=1):
        share = f"{100.0 * count / total:.2f}%"
        print(f"| {rank:^8d} | {name:^26} | {count:^21d} | {share:^20} |")
    print("-" * REPORT_WIDTH)

    # Входи за відділами: Counter із генератором
    by_department = Counter(users_db[u]["department"] for u in events if u in users_db)
    dept_line = ", ".join(f"{d}: {n}" for d, n in by_department.most_common())
    print(f"  Входи за відділами:                    {dept_line}")

    # Множинні перевірки журналу входів проти реєстру
    known, logged = set(users_db), set(freq)
    unknown_accounts = logged - known
    inactive_logins = {u for u in logged & known if not users_db[u]["is_active"]}
    dormant_active = {u for u in known - logged if users_db[u]["is_active"]}

    print(f"  Невідомі облікові записи у журналі:    {sorted(unknown_accounts) or '-'}")
    print(f"  Входи неактивних облікових записів:    {sorted(inactive_logins) or '-'}")
    print(f"  Активні записи без жодного входу:      {sorted(dormant_active) or '-'}")
    print("=" * REPORT_WIDTH)


def print_summary(users_db: dict, results: dict[str, dict]) -> None:
    """Виводить підсумок аудиту."""
    active = [n for n, u in users_db.items() if u["is_active"]]
    avg_j = sum(results[n]["jaccard"] for n in active) / len(active)
    excess_total = sum(len(r["excess"]) for n, r in results.items() if users_db[n]["is_active"])
    statuses = Counter(r["status"] for r in results.values())

    print(f"\n{'ПІДСУМОК АУДИТУ':^{REPORT_WIDTH}}")
    print("-" * REPORT_WIDTH)
    print(f"  Облікових записів / активних:          {len(users_db)} / {len(active)}")
    print(f"  Середній J(A, B) активних записів:     {avg_j:.4f} ({avg_j * 100:.2f}%)")
    print(f"  Сумарно надлишкових прав у активних:   {excess_total}")
    print(f"  Розподіл статусів:                     {dict(statuses)}")
    print("=" * REPORT_WIDTH + "\n")


def main() -> None:
    """Головна точка входу модуля аудиту доступу."""
    t_start = time.perf_counter()

    users_db = create_initial_user_database()
    results = audit_all_users(users_db)

    print()
    print_audit_table(users_db, results)
    print_login_analysis(users_db, LOGIN_EVENTS)
    print_summary(users_db, results)

    elapsed = time.perf_counter() - t_start
    print(f"Час виконання модуля аудиту доступу: {elapsed * 1000:.3f} мс\n")


if __name__ == "__main__":
    main()
