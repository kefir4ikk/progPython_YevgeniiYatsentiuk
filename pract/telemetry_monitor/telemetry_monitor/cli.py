"""Командний рядок і головна функція обробки журналу."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Sequence

from .analytics import aggregate, filter_records
from .exceptions import (
    ErrorThresholdExceededError,
    RecordError,
    StorageError,
    TelemetryError,
)
from .parser import ParseStats, parse_stream
from .report import Summary, write_report
from .sensors import known_kinds
from .storage import LogReader, open_report

__all__ = ["process_log", "build_parser", "main"]

log = logging.getLogger("telemetry_monitor")

EXIT_OK = 0
EXIT_STORAGE = 3
EXIT_DATA = 4
EXIT_INTERNAL = 70


def process_log(path: str, *, strict: bool = False,
                max_error_ratio: float = 0.5,
                kinds: Sequence[str] | None = None,
                nodes: Sequence[str] | None = None,
                critical_only: bool = False) -> Summary:
    """Читає журнал, розбирає, фільтрує й агрегує дані.

    try/except/else/finally тут виконують чотири різні ролі:
    try — небезпечна робота з файлом; except — журналювання збою
    (виняток передається далі); else — перевірка частки пошкоджених
    записів, яка має сенс лише при успішному читанні; finally —
    діагностика часу, що виконується завжди.
    """
    stats = ParseStats()
    started = time.perf_counter()
    try:
        with LogReader(path) as reader:
            records = parse_stream(reader.lines(), strict=strict,
                                   stats=stats)
            selected = filter_records(records, kinds=kinds, nodes=nodes,
                                      critical_only=critical_only)
            result = aggregate(selected)
    except StorageError as exc:
        log.debug("збій доступу до файлу: %s", exc)
        raise
    except RecordError as exc:      # можливо лише в суворому режимі
        log.debug("суворий режим зупинено: %s", exc)
        raise
    else:
        summary = Summary(str(path), stats, result)
        if summary.rejected_ratio > max_error_ratio:
            raise ErrorThresholdExceededError(
                f"відхилено {summary.rejected_ratio:.1%} записів, "
                f"дозволено не більше {max_error_ratio:.1%}")
        return summary
    finally:
        elapsed = time.perf_counter() - started
        log.debug("обробку завершено за %.4f с; рядків: %d",
                  elapsed, stats.lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="telemetry_monitor",
        description="Аналіз журналу телеметрії сенсорів мережі.")
    parser.add_argument("log", help="шлях до текстового журналу")
    parser.add_argument("-o", "--output", metavar="ФАЙЛ",
                        help="записати звіт у файл (за замовчуванням — "
                             "у стандартний вивід)")
    parser.add_argument("--kind", nargs="+", choices=known_kinds(),
                        metavar="ТИП", help="лише вказані типи сенсорів")
    parser.add_argument("--node", nargs="+", metavar="ВУЗОЛ",
                        help="лише вказані вузли")
    parser.add_argument("--critical-only", action="store_true",
                        help="враховувати лише критичні показання")
    parser.add_argument("--strict", action="store_true",
                        help="зупинитися на першому пошкодженому записі")
    parser.add_argument("--max-error-ratio", type=float, default=0.5,
                        metavar="ЧАСТКА",
                        help="допустима частка пошкоджених записів "
                             "(0..1, за замовчуванням 0.5)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="діагностичні повідомлення")
    return parser


def _make_streams_safe() -> None:
    """Консоль Windows (cp1251/cp866) не знає деяких символів: замість
    UnicodeEncodeError небезпечні символи замінюються на «?»."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


def _silence_stdout() -> None:
    """Спрямовує stdout у «нікуди», щоб інтерпретатор не лаявся при виході."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except (OSError, ValueError):   # stdout без дескриптора (тести)
        pass


def main(argv: Sequence[str] | None = None) -> int:
    _make_streams_safe()
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s")
    if not 0.0 <= args.max_error_ratio <= 1.0:
        print("помилка: --max-error-ratio має бути в межах 0..1",
              file=sys.stderr)
        return 2
    try:
        summary = process_log(
            args.log, strict=args.strict,
            max_error_ratio=args.max_error_ratio, kinds=args.kind,
            nodes=args.node, critical_only=args.critical_only)
        with open_report(args.output) as handle:
            write_report(summary, handle)
    except StorageError as exc:
        print(f"помилка файлу: {exc}", file=sys.stderr)
        return EXIT_STORAGE
    except TelemetryError as exc:
        print(f"помилка даних: {exc}", file=sys.stderr)
        return EXIT_DATA
    except BrokenPipeError:
        # Споживач виводу закрив канал (| Select-Object -First 5, | head):
        # це не помилка програми. Решту виводу відкидаємо мовчки.
        _silence_stdout()
        return EXIT_OK
    except Exception as exc:  # остання межа: програма не падає з traceback
        print(f"внутрішня помилка: {exc!r}", file=sys.stderr)
        return EXIT_INTERNAL
    if args.output:
        print(f"Звіт записано: {args.output}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())