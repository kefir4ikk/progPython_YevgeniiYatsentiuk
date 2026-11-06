"""
Пакет системних утиліт обробки та аудиту файлової системи fs_toolkit.
Освітній компонент: Програмування на Python.
"""

from .scanner import find_empty_directories, remove_empty_directories
from .reporter import print_cleanup_report

# Суворий експорт публічного інтерфейсу пакета: внутрішні функції (_read_metadata,
# _short_path) із префіксом підкреслення назовні не експортуються
__all__ = [
    "find_empty_directories",
    "remove_empty_directories",
    "print_cleanup_report",
]
