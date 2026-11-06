"""
Модуль сканування файлової системи (бізнес-логіка): пошук порожніх директорій
та їхнє безпечне видалення з режимом імітації.

Каталог вважається порожнім, якщо його піддерево не містить жодного файлу
(допускаються лише вкладені порожні підкаталоги). Символьні посилання, сокети та
приховані файли (наприклад, .keep) трактуються як вміст, тому каталог із ними
порожнім не вважається.
Освітній компонент: Програмування на Python.
"""

import time
from pathlib import Path


def _read_metadata(directory: Path) -> tuple[str, str]:
    """
    Одним викликом stat() повертає кортеж (час_модифікації, права_доступу):
    час у форматі 'РРРР-ММ-ДД ГГ:ХХ', права як вісімкова маска POSIX (st_mode & 0o777).
    """
    try:
        stat_res = directory.stat()
        modified = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat_res.st_mtime))
        permissions = oct(stat_res.st_mode & 0o777)
        return modified, permissions
    except OSError:
        return "—", "—"


def find_empty_directories(base_path: Path) -> dict:
    """
    Рекурсивно знаходить порожні директорії в піддереві base_path.

    Алгоритм:
      1. Один рекурсивний прохід Path.rglob("*") розділяє вузли на каталоги та решту
         об'єктів (файли, символьні посилання, сокети).
      2. Каталоги сортуються за глибиною від найглибших до найвищих.
      3. Каталог порожній, якщо кожен його елемент - уже визнаний порожнім каталог
         (або елементів немає взагалі). Завдяки порядку «знизу вгору» батьківський
         каталог перевіряється після дочірніх.
    Повертає словник: empty_dirs (від найглибших), dirs_scanned, objects_seen,
    unreadable та root_is_empty.
    """
    if not base_path.exists() or not base_path.is_dir():
        raise ValueError(f"Шлях '{base_path}' не існує або не є директорією.")

    directories: list[Path] = []
    objects_seen = 0

    # Крок 1. Єдиний рекурсивний обхід; rglob не заходить у символьні посилання на каталоги
    for item in base_path.rglob("*"):
        if item.is_dir() and not item.is_symlink():
            directories.append(item)
        else:
            objects_seen += 1

    # Крок 2. Найглибші каталоги першими; шлях у ключі робить порядок детермінованим
    directories.sort(key=lambda p: (-len(p.relative_to(base_path).parts), str(p)))

    empty_set: set[Path] = set()
    empty_dirs: list[dict] = []
    unreadable: list[tuple[Path, str]] = []

    # Крок 3. Перевірка предиката порожнечі знизу вгору
    for directory in directories:
        try:
            entries = list(directory.iterdir())
        except OSError as err:                       # PermissionError є підкласом OSError
            unreadable.append((directory, str(err)))  # вміст невідомий - не чіпаємо
            continue

        if all(entry in empty_set for entry in entries):
            empty_set.add(directory)
            modified_at, permissions = _read_metadata(directory)
            empty_dirs.append({
                "path": directory,
                "relative_path": directory.relative_to(base_path),
                "depth": len(directory.relative_to(base_path).parts),
                "direct_entries": len(entries),
                "kind": "порожня" if not entries else "підкаталоги",
                "modified_at": modified_at,
                "permissions": permissions,
            })

    # Кореневий каталог лише перевіряється, але ніколи не видаляється
    try:
        root_is_empty = all(entry in empty_set for entry in base_path.iterdir())
    except OSError as err:
        unreadable.append((base_path, str(err)))
        root_is_empty = False

    return {
        "empty_dirs": empty_dirs,
        "dirs_scanned": len(directories) + 1,        # +1 - сам кореневий каталог
        "objects_seen": objects_seen,
        "unreadable": unreadable,
        "root_is_empty": root_is_empty,
    }


def remove_empty_directories(empty_dirs: list[dict], dry_run: bool = True) -> list[dict]:
    """
    Обробляє список порожніх каталогів у порядку від найглибших до батьківських.
    У режимі dry_run нічого не змінює, а лише позначає дії як «СИМУЛЯЦІЯ».
    Інакше видаляє каталог методом Path.rmdir(), який за задумом видаляє
    виключно порожні каталоги й генерує OSError, якщо каталог не порожній.
    Повертає список записів із доданими полями status та error.
    """
    actions: list[dict] = []
    for record in empty_dirs:
        action = dict(record)
        action["error"] = ""
        if dry_run:
            action["status"] = "СИМУЛЯЦІЯ"
        else:
            try:
                record["path"].rmdir()
                action["status"] = "ВИДАЛЕНО"
            except OSError as err:
                action["status"] = "ПОМИЛКА"
                action["error"] = str(err)
        actions.append(action)
    return actions
