"""
Лабораторна робота № 6. Модуль 1. Варіант 2.
Інвентаризація користувачів Active Directory: маніпуляції словниками (dict),
безпечний доступ через get()/setdefault(), оновлення через update(),
вилучення через pop() та інвертований індекс «роль -> користувачі»
за допомогою Dict Comprehension.

Структура запису: Username -> {email, department, roles (set), is_active}
Освітній компонент: Програмування на Python.
"""

import textwrap
import time

REPORT_WIDTH: int = 88


def create_initial_user_database() -> dict[str, dict]:
    """
    Створює первинний реєстр користувачів Active Directory.
    Ключ: Username (str). Значення: словник параметрів облікового запису.
    """
    users_db = {
        "asmirnova": {
            "email": "a.smirnova@corp.local",
            "department": "IT",
            "roles": {"domain_users", "vpn_access", "remote_desktop",
                      "admin_console", "file_share_read", "monitoring_view"},
            "is_active": True,
        },
        "pkovalenko": {
            "email": "p.kovalenko@corp.local",
            "department": "IT",
            "roles": {"domain_users", "vpn_access", "remote_desktop", "admin_console",
                      "file_share_read", "file_share_write", "db_write"},
            "is_active": True,
        },
        "nhavrylenko": {
            "email": "n.havrylenko@corp.local",
            "department": "IT",
            "roles": {"admin_console", "vpn_access"},
            "is_active": False,
        },
        "mpetrenko": {
            "email": "m.petrenko@corp.local",
            "department": "Finance",
            "roles": {"domain_users", "file_share_read", "file_share_write",
                      "payroll_access", "erp_access", "admin_console"},
            "is_active": True,
        },
        "okuzmenko": {
            "email": "o.kuzmenko@corp.local",
            "department": "Finance",
            "roles": {"domain_users", "file_share_read", "payroll_access"},
            "is_active": True,
        },
        "dshevchenko": {
            "email": "d.shevchenko@corp.local",
            "department": "HR",
            "roles": {"domain_users", "file_share_read", "hr_portal", "recruiting_tool"},
            "is_active": True,
        },
        "ibondar": {
            "email": "i.bondar@corp.local",
            "department": "HR",
            "roles": {"domain_users", "hr_portal", "vpn_access", "remote_desktop"},
            "is_active": True,
        },
        "tmelnyk": {
            "email": "t.melnyk@corp.local",
            "department": "Sales",
            "roles": {"domain_users", "file_share_read", "crm_access", "vpn_access"},
            "is_active": True,
        },
        "kromanenko": {
            "email": "k.romanenko@corp.local",
            "department": "Sales",
            "roles": {"domain_users", "crm_access"},
            "is_active": True,
        },
        "vlysenko": {
            "email": "v.lysenko@corp.local",
            "department": "Sales",
            "roles": {"domain_users", "crm_access", "vpn_access"},
            "is_active": False,
        },
    }
    return users_db


def add_or_update_user(users_db: dict, username: str, user_info: dict) -> None:
    """
    Додає нового користувача або оновлює поля існуючого облікового запису
    за допомогою методу update() (злиття словників).
    """
    if username in users_db:
        users_db[username].update(user_info)
    else:
        users_db[username] = user_info


def remove_user(users_db: dict, username: str) -> dict | None:
    """
    Вилучає обліковий запис методом pop() із значенням за замовчуванням None,
    що запобігає виникненню KeyError для неіснуючого користувача.
    """
    removed = users_db.pop(username, None)
    if removed is None:
        print(f"Попередження: спроба видалення неіснуючого користувача '{username}'.")
    return removed


def get_user_email(users_db: dict, username: str) -> str:
    """Безпечний пошук e-mail через get(): для відсутнього ключа повертає '—' замість KeyError."""
    return users_db.get(username, {}).get("email", "—")


def grant_role(users_db: dict, username: str, role: str) -> None:
    """
    Надає користувачеві роль. Метод setdefault() гарантує наявність множини ролей:
    якщо ключа 'roles' ще немає, він створюється порожньою множиною.
    """
    users_db[username].setdefault("roles", set()).add(role)


def revoke_role(users_db: dict, username: str, role: str) -> None:
    """Відкликає роль; discard() не генерує виняток, якщо ролі в множині немає."""
    users_db[username].setdefault("roles", set()).discard(role)


def build_inverted_role_index(users_db: dict) -> dict[str, list[str]]:
    """
    Будує інвертований індекс «роль -> відсортований список користувачів»
    за допомогою Dict Comprehension.
    """
    # 1. Множина всіх унікальних ролей у реєстрі (set comprehension)
    all_roles = {role for data in users_db.values() for role in data.get("roles", set())}

    # 2. Генерація індексу Role -> [Usernames]
    return {
        role: sorted(name for name, data in users_db.items() if role in data.get("roles", set()))
        for role in sorted(all_roles)
    }


def print_inventory_report(users_db: dict, inverted_index: dict) -> None:
    """Виводить відформатований звіт інвентаризації та інвертований індекс ролей."""
    header = (f"| {'Username':<16} | {'E-mail':<32} | {'Відділ':<10} | "
              f"{'Активний':^8} | {'Ролей':^6} |")
    print("=" * REPORT_WIDTH)
    print(f"{'РЕЄСТР КОРИСТУВАЧІВ ACTIVE DIRECTORY':^{REPORT_WIDTH}}")
    print("=" * REPORT_WIDTH)
    print(header)
    print("-" * REPORT_WIDTH)
    for username, data in sorted(users_db.items()):
        active = "Так" if data["is_active"] else "Ні"
        print(f"| {username:<16} | {data['email']:<32} | {data['department']:<10} | "
              f"{active:^8} | {len(data['roles']):^6d} |")

    print("=" * REPORT_WIDTH)
    print(f"{'ІНВЕРТОВАНИЙ ІНДЕКС: РОЛЬ -> СПИСОК КОРИСТУВАЧІВ':^{REPORT_WIDTH}}")
    print("-" * REPORT_WIDTH)
    for role, names in inverted_index.items():
        line = f"  {role:<18}: " + ", ".join(names)
        # Довгі списки переносяться з відступом, щоб не виходити за ширину звіту
        print(textwrap.fill(line, width=REPORT_WIDTH, subsequent_indent=" " * 22))
    print("=" * REPORT_WIDTH + "\n")


def main() -> None:
    """Головна точка входу модуля інвентаризації користувачів."""
    t_start = time.perf_counter()

    # 1. Створення реєстру
    users_db = create_initial_user_database()
    print(f"Початковий розмір реєстру: {len(users_db)} облікових записів")

    # 2. CRUD: додавання нового користувача
    add_or_update_user(users_db, "ysavchenko", {
        "email": "y.savchenko@corp.local",
        "department": "HR",
        "roles": {"domain_users"},
        "is_active": True,
    })

    # 3. CRUD: оновлення існуючого запису через update() (зміна e-mail)
    add_or_update_user(users_db, "okuzmenko", {"email": "olena.kuzmenko@corp.local"})

    # 4. Безпечний доступ get(): існуючий та відсутній користувач
    print(f"get_user_email('okuzmenko') -> {get_user_email(users_db, 'okuzmenko')}")
    print(f"get_user_email('ghost_user') -> {get_user_email(users_db, 'ghost_user')}")

    # 5. setdefault(): надання ролі та відкликання зайвого права
    grant_role(users_db, "ysavchenko", "hr_portal")
    revoke_role(users_db, "pkovalenko", "db_write")

    # 6. CRUD: вилучення звільненого користувача та неіснуючого запису
    removed = remove_user(users_db, "vlysenko")
    print(f"Вилучено запис: vlysenko (відділ {removed['department']})")
    remove_user(users_db, "ghost_user")
    print()

    # 7. Інвертований індекс і звіт
    role_index = build_inverted_role_index(users_db)
    print_inventory_report(users_db, role_index)

    elapsed = time.perf_counter() - t_start
    print(f"Час виконання модуля інвентаризації: {elapsed * 1000:.3f} мс\n")


if __name__ == "__main__":
    main()
