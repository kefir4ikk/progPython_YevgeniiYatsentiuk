"""
РГР. Модуль parser: імпорт, нормалізація та валідація вхідного робочого навантаження.

Підтримуються два формати рядків (регістр не враховується, коментар починається з '#'):
    1) ключ-значення:  P1 arrival=0 burst=24     (синоніми ключів: at, bt)
    2) CSV-подібний:   P1, 0, 24                  (роздільники ',' або ';')
Необов'язковий рядок-заголовок 'pid,arrival,burst' ігнорується.

Етапи обробки рядка: нормалізація (рядкові методи та re.sub) -> зіставлення з шаблонами
re -> створення Process (валідація атрибутів). Помилки перетворюються на винятки
ієрархії InputFormatError із номером рядка та ланцюжком причини (raise ... from).
Освітній компонент: Програмування на Python.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from .exceptions import (EmptyWorkloadError, InputFormatError, InvalidLineSyntaxError,
                         ProcessParameterError, WorkloadReadError)
from .models import Process, Workload

__all__ = ["normalize_line", "parse_line", "parse_workload_text", "load_workload"]

_PID = r"(?P<pid>[A-Za-z][A-Za-z0-9_-]{0,15})"
_NUM = r"(?P<{0}>\d+)"

# Шаблон 1: ключ-значення
_KEY_VALUE = re.compile(
    rf"^{_PID}\s+(?:arrival|at)\s*=\s*{_NUM.format('arrival')}"
    rf"\s+(?:burst|bt)\s*=\s*{_NUM.format('burst')}$", re.IGNORECASE)

# Шаблон 2: CSV-подібний рядок
_CSV_LIKE = re.compile(
    rf"^{_PID}\s*[,;]\s*{_NUM.format('arrival')}\s*[,;]\s*{_NUM.format('burst')}$")

# Рядок-заголовок CSV
_HEADER = re.compile(r"^pid\s*[,;]\s*arrival\s*[,;]\s*burst$", re.IGNORECASE)

_COMMENT = re.compile(r"#.*$")
_SPACES = re.compile(r"\s+")


def normalize_line(raw: str) -> str:
    """Прибирає BOM, коментар і зайві пробіли; повертає порожній рядок для службових рядків."""
    text = raw.replace("﻿", "").replace(" ", " ")
    text = _COMMENT.sub("", text)
    return _SPACES.sub(" ", text).strip()


def parse_line(line_no: int, raw: str) -> Process | None:
    """Розбирає один рядок; повертає None для порожніх рядків, коментарів і заголовка."""
    line = normalize_line(raw)
    if not line or _HEADER.match(line):
        return None
    match = _KEY_VALUE.match(line) or _CSV_LIKE.match(line)
    if match is None:
        raise InvalidLineSyntaxError(line_no, raw.strip())
    try:
        return Process(match["pid"], int(match["arrival"]), int(match["burst"]))
    except ProcessParameterError as exc:
        # Ланцюжок винятків: початкова причина зберігається в exc.__cause__
        raise InputFormatError(f"Рядок {line_no}: {exc}", error_code=3004) from exc


def parse_workload_text(text: str) -> Workload:
    """Розбирає багаторядковий текст у Workload; порожній результат - EmptyWorkloadError."""
    workload = Workload()
    for line_no, raw in enumerate(text.splitlines(), start=1):
        process = parse_line(line_no, raw)
        if process is not None:
            workload.add(process)           # DuplicateProcessError при повторі pid
    if len(workload) == 0:
        raise EmptyWorkloadError()
    return workload


def load_workload(path: str | Path) -> Workload:
    """Читає файл навантаження через менеджер контексту (кодування utf-8, BOM допускається)."""
    if os.path.isdir(path):
        raise WorkloadReadError(f"Шлях {str(path)!r} є каталогом, а не файлом навантаження.")
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise WorkloadReadError(f"Не вдалося прочитати файл {str(path)!r}: {exc}") from exc
    return parse_workload_text(text)
