"""Утиліта зчитування та аналізу телеметрії сенсорів мережі (варіант 1)."""

from .analytics import aggregate, filter_records
from .cli import main, process_log
from .exceptions import TelemetryError
from .parser import parse_line, parse_stream

__all__ = [
    "TelemetryError",
    "aggregate",
    "filter_records",
    "main",
    "parse_line",
    "parse_stream",
    "process_log",
]

__version__ = "1.0.0"