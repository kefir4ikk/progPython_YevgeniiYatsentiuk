"""Ієрархія користувацьких винятків утиліти телеметричного моніторингу.

Дерево успадкування:

    TelemetryError
    ├── RecordError                    пошкоджений запис журналу
    │   ├── MalformedRecordError       рядок не відповідає шаблону
    │   ├── InvalidStatusError         некоректний регістр стану
    │   ├── ValueOutOfRangeError       значення поза фізичним діапазоном
    │   ├── InvalidTimestampError      неіснуюча дата або час
    │   └── UnknownSensorKindError     невідомий тип сенсора
    ├── StorageError                   помилка доступу до файлової системи
    │   ├── LogNotFoundError           журнал не знайдено
    │   ├── LogAccessError             немає прав або читання неможливе
    │   └── ReportWriteError           не вдалося записати звіт
    └── ErrorThresholdExceededError    забагато пошкоджених записів
"""

from __future__ import annotations

__all__ = [
    "TelemetryError",
    "RecordError",
    "MalformedRecordError",
    "InvalidStatusError",
    "ValueOutOfRangeError",
    "InvalidTimestampError",
    "UnknownSensorKindError",
    "StorageError",
    "LogNotFoundError",
    "LogAccessError",
    "ReportWriteError",
    "ErrorThresholdExceededError",
]


class TelemetryError(Exception):
    """Базовий виняток: уся програма ловить саме його."""

    code = 1000

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return f"[E{self.code}] {self.message}"


class RecordError(TelemetryError):
    """Запис журналу пошкоджений; обробку можна продовжити з наступного."""

    code = 2000

    def __init__(self, message: str, *, line_no: int | None = None,
                 raw: str | None = None) -> None:
        super().__init__(message)
        self.line_no = line_no
        self.raw = raw

    def __str__(self) -> str:
        where = f"рядок {self.line_no}: " if self.line_no else ""
        return f"[E{self.code}] {where}{self.message}"


class MalformedRecordError(RecordError):
    code = 2001


class InvalidStatusError(RecordError):
    code = 2002


class ValueOutOfRangeError(RecordError):
    code = 2003


class InvalidTimestampError(RecordError):
    code = 2004


class UnknownSensorKindError(RecordError):
    code = 2005


class StorageError(TelemetryError):
    """Збій файлової системи; продовжувати обробку немає сенсу."""

    code = 3000


class LogNotFoundError(StorageError):
    code = 3001


class LogAccessError(StorageError):
    code = 3002


class ReportWriteError(StorageError):
    code = 3003


class ErrorThresholdExceededError(TelemetryError):
    """Частка відхилених записів перевищила дозволену межу."""

    code = 4000