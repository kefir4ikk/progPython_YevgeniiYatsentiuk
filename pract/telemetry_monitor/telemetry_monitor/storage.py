"""Безпечний доступ до файлів: менеджери контексту для читання й запису.

Обидва менеджери побудовані за принципом RAII: ресурс захоплюється в
``__enter__`` і гарантовано звільняється в ``__exit__``, навіть якщо
всередині блоку ``with`` виникло виключення.
"""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
from pathlib import Path
from typing import IO, Iterator

from .exceptions import (
    LogAccessError,
    LogNotFoundError,
    ReportWriteError,
)

__all__ = ["LogReader", "AtomicWriter", "open_report"]


class LogReader:
    """Потокове читання журналу з перекладом OSError у власні винятки."""

    def __init__(self, path: str | os.PathLike) -> None:
        self._path = Path(path)
        self._handle: IO[str] | None = None

    def __enter__(self) -> "LogReader":
        try:
            # utf-8-sig: прибирає BOM, який додає Блокнот Windows.
            # errors="replace": биті байти не валять програму, а лише
            # дають рядок, який не пройде перевірку шаблоном.
            self._handle = open(self._path, "r", encoding="utf-8-sig",
                                errors="replace", newline=None)
        except FileNotFoundError as exc:
            raise LogNotFoundError(
                f"журнал {self._path} не знайдено") from exc
        except OSError as exc:  # PermissionError, IsADirectoryError, ...
            raise LogAccessError(
                f"немає доступу до {self._path}: {exc.strerror}") from exc
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
        return False   # виняток не гасимо

    def lines(self) -> Iterator[str]:
        """Ліниво віддає рядки без символу переведення рядка."""
        if self._handle is None:
            raise ValueError("LogReader використано поза блоком with")
        try:
            for line in self._handle:
                yield line.rstrip("\n")
        except OSError as exc:
            raise LogAccessError(
                f"помилка читання {self._path}: {exc.strerror}") from exc


class AtomicWriter:
    """Запис звіту через тимчасовий файл і атомарну заміну.

    Якщо блок ``with`` завершується виключенням, цільовий файл лишається
    таким, яким був, а тимчасовий видаляється. Читач ніколи не побачить
    наполовину записаний звіт.
    """

    def __init__(self, path: str | os.PathLike) -> None:
        self._path = Path(path)
        self._tmp_name: str | None = None
        self._handle: IO[str] | None = None

    def __enter__(self) -> IO[str]:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, self._tmp_name = tempfile.mkstemp(
                dir=self._path.parent, prefix=self._path.name + ".",
                suffix=".tmp")
            self._handle = os.fdopen(fd, "w", encoding="utf-8",
                                     newline="\n")
        except OSError as exc:
            raise ReportWriteError(
                f"не вдалося створити {self._path}: {exc.strerror}"
            ) from exc
        return self._handle

    def __exit__(self, exc_type, exc, tb) -> bool:
        assert self._handle is not None and self._tmp_name is not None
        try:
            if exc_type is None:
                self._handle.flush()
                os.fsync(self._handle.fileno())
            self._handle.close()
            if exc_type is None:
                os.replace(self._tmp_name, self._path)
        except OSError as err:
            raise ReportWriteError(
                f"не вдалося записати {self._path}: {err.strerror}"
            ) from err
        finally:
            if os.path.exists(self._tmp_name):
                os.unlink(self._tmp_name)
        return False


@contextlib.contextmanager
def open_report(path: str | os.PathLike | None) -> Iterator[IO[str]]:
    """Той самий патерн у стилі contextlib: файл або стандартний вивід."""
    if path is None:
        yield sys.stdout
        return
    with AtomicWriter(path) as handle:
        yield handle