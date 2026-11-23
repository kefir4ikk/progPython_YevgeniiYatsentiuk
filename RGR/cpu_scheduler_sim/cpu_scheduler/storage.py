"""
РГР. Модуль storage: збереження та завантаження звітів у форматах JSON і CSV.

Усі файлові операції виконуються через менеджери контексту `with open(...)`, що гарантує
закриття дескриптора навіть за виняткової ситуації. Помилки ОС (OSError) перетворюються
на ReportWriteError / ReportReadError із збереженням причини (raise ... from exc).
Освітній компонент: Програмування на Python.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from .exceptions import ReportReadError, ReportWriteError
from .models import ScheduleResult

__all__ = ["save_json", "load_json", "save_csv", "save_comparison_csv", "save_comparison_json"]

PROCESS_FIELDS = ["pid", "arrival", "burst", "first_start", "completion",
                  "turnaround", "waiting", "response"]
COMPARISON_FIELDS = ["algorithm", "avg_waiting", "avg_turnaround", "avg_response",
                     "avg_slowdown", "max_waiting", "makespan", "utilization_percent",
                     "throughput", "context_switches", "idle_time", "switch_time"]
REQUIRED_KEYS = ("algorithm", "parameters", "metrics", "processes", "segments")


def _prepare(path: str | Path) -> Path:
    """Створює каталог призначення (os.makedirs) і повертає шлях як Path."""
    directory = os.path.dirname(os.path.abspath(os.fspath(path)))
    os.makedirs(directory, exist_ok=True)
    return Path(path)


def save_json(result: ScheduleResult, path: str | Path) -> Path:
    """Зберігає повний звіт (параметри, показники, процеси, інтервали) у JSON."""
    try:
        target = _prepare(path)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(result.to_dict(), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise ReportWriteError(f"Не вдалося записати {str(path)!r}: {exc}") from exc
    return target


def load_json(path: str | Path) -> dict:
    """Завантажує звіт і перевіряє наявність обов'язкових ключів."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportReadError(f"Не вдалося прочитати {str(path)!r}: {exc}") from exc
    if not isinstance(data, dict) or any(key not in data for key in REQUIRED_KEYS):
        raise ReportReadError(f"Файл {str(path)!r} не є звітом симулятора: "
                              f"відсутні ключі {REQUIRED_KEYS}.")
    return data


def save_csv(result: ScheduleResult, path: str | Path) -> Path:
    """Зберігає таблицю показників по процесах у CSV (кодування utf-8, роздільник кома)."""
    try:
        target = _prepare(path)
        with open(target, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=PROCESS_FIELDS)
            writer.writeheader()
            for item in result:
                writer.writerow(item.to_dict())
    except OSError as exc:
        raise ReportWriteError(f"Не вдалося записати {str(path)!r}: {exc}") from exc
    return target


def save_comparison_csv(results: list[ScheduleResult], path: str | Path) -> Path:
    """Зберігає порівняльну таблицю агрегованих показників кількох прогонів."""
    try:
        target = _prepare(path)
        with open(target, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COMPARISON_FIELDS)
            writer.writeheader()
            for result in results:
                writer.writerow(result.summary())
    except OSError as exc:
        raise ReportWriteError(f"Не вдалося записати {str(path)!r}: {exc}") from exc
    return target


def save_comparison_json(results: list[ScheduleResult], path: str | Path) -> Path:
    """Зберігає агреговані показники кількох прогонів у JSON."""
    try:
        target = _prepare(path)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump([r.summary() for r in results], handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise ReportWriteError(f"Не вдалося записати {str(path)!r}: {exc}") from exc
    return target
