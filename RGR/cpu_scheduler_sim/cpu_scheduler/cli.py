"""
РГР. Модуль cli: консольний інтерфейс, ручний розбір параметрів командного рядка sys.argv.

Команди:
    run        - один прогін (fifo або rr) з виведенням таблиці, показників і діаграми Ганта;
    compare    - FIFO та RR для набору квантів; порівняльна таблиця;
    benchmark  - вимірювання швидкодії для зростаючих розмірів навантаження;
    generate   - створення псевдовипадкового файлу навантаження.

Коди завершення процесу:
    0 - успіх; 1 - синтаксис аргументів; 2 - вхідні дані (файл, формат); 3 - некоректні параметри;
    4 - збій симуляції; 5 - помилка запису/читання звіту; 6 - інша помилка пакета; 70 - внутрішня помилка.
Освітній компонент: Програмування на Python.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import __version__
from .benchmark import estimate_exponent, generate_workload, run_benchmark, workload_to_text
from .exceptions import (CliUsageError, InputFormatError, ProcessParameterError, ReportWriteError,
                         SchedulerConfigError, SchedulerError, SimulationError, StorageError,
                         WorkloadReadError)
from .parser import load_workload
from .reporting import (render_comparison, render_gantt, render_summary, render_table,
                        render_workload)
from .schedulers import DEFAULT_MAX_SLICES, FIFOScheduler, RoundRobinScheduler, create_scheduler
from .storage import save_comparison_csv, save_comparison_json, save_csv, save_json

__all__ = ["main", "parse_options", "exit_code_for"]

USAGE = """\
cpu_scheduler - симулятор диспетчеризації черги процесів CPU (FIFO, Round Robin).

ВИКОРИСТАННЯ:
    python cli_main.py run       --input <файл> [--algo fifo|rr] [--quantum N] [--switch-cost S]
                                 [--max-slices M] [--gantt] [--json <файл>] [--csv <файл>]
    python cli_main.py compare   --input <файл> [--quanta 2,4,8] [--switch-cost S]
                                 [--json <файл>] [--csv <файл>]
    python cli_main.py benchmark [--sizes 100,1000,10000] [--quantum N] [--repeats K] [--csv <файл>]
    python cli_main.py generate  --count N --output <файл> [--seed X]
    python cli_main.py --help | --version

ФОРМАТ ВХІДНОГО ФАЙЛУ (рядок на процес, коментар після '#'):
    P1 arrival=0 burst=24        або        P1, 0, 24

КОДИ ЗАВЕРШЕННЯ: 0 успіх, 1 аргументи, 2 вхідні дані, 3 параметри, 4 симуляція, 5 звіти, 70 збій
"""

# Специфікації прапорців кожної команди: ім'я -> True, якщо прапорець приймає значення
COMMAND_SPECS = {
    "run": {"--input": True, "--algo": True, "--quantum": True, "--switch-cost": True,
            "--max-slices": True, "--json": True, "--csv": True, "--gantt": False},
    "compare": {"--input": True, "--quanta": True, "--switch-cost": True, "--json": True,
                "--csv": True},
    "benchmark": {"--sizes": True, "--quantum": True, "--repeats": True, "--csv": True},
    "generate": {"--count": True, "--output": True, "--seed": True},
}


def parse_options(args: list[str], spec: dict[str, bool]) -> dict[str, str | bool]:
    """Розбирає ['--ключ', 'значення', '--прапорець', ...] згідно зі специфікацією команди."""
    options: dict[str, str | bool] = {}
    i = 0
    while i < len(args):
        flag = args[i]
        if flag not in spec:
            raise CliUsageError(f"Невідомий параметр {flag!r}.")
        if spec[flag]:                                   # прапорець зі значенням
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                raise CliUsageError(f"Після {flag} необхідно вказати значення.")
            options[flag] = args[i + 1]
            i += 2
        else:                                            # прапорець без значення
            options[flag] = True
            i += 1
    return options


def _int_option(options: dict, flag: str, default: int | None, error_cls: type[SchedulerError]) -> int | None:
    """Читає цілочисловий параметр; нечисловий рядок перетворюється на error_cls."""
    if flag not in options:
        return default
    try:
        return int(options[flag])
    except ValueError:
        raise error_cls(f"Параметр {flag} має бути цілим числом, отримано {options[flag]!r}.") from None


def _int_list(options: dict, flag: str, default: str) -> list[int]:
    raw = str(options.get(flag, default))
    try:
        return [int(part) for part in raw.split(",") if part.strip()]
    except ValueError:
        raise CliUsageError(f"Параметр {flag} має бути списком цілих через кому: {raw!r}.") from None


def _require(options: dict, flag: str) -> str:
    if flag not in options:
        raise CliUsageError(f"Обов'язковий параметр {flag} не вказано.")
    return str(options[flag])


def _cmd_run(options: dict) -> None:
    workload = load_workload(_require(options, "--input"))
    scheduler = create_scheduler(
        str(options.get("--algo", "rr")),
        quantum=_int_option(options, "--quantum", 4, SchedulerConfigError),
        switch_cost=_int_option(options, "--switch-cost", 0, SchedulerConfigError),
        max_slices=_int_option(options, "--max-slices", DEFAULT_MAX_SLICES, SchedulerConfigError))
    result = scheduler.schedule(workload)

    print(render_workload(workload), end="\n\n")
    print(render_table(result), end="\n\n")
    print(render_summary(result))
    if options.get("--gantt"):
        print("\nДіаграма Ганта:")
        print(render_gantt(result))
    if "--json" in options:
        print(f"\nJSON-звіт збережено: {save_json(result, str(options['--json']))}")
    if "--csv" in options:
        print(f"CSV-звіт збережено:  {save_csv(result, str(options['--csv']))}")


def _cmd_compare(options: dict) -> None:
    workload = load_workload(_require(options, "--input"))
    switch_cost = _int_option(options, "--switch-cost", 0, SchedulerConfigError)
    quanta = _int_list(options, "--quanta", "2,4,8")
    schedulers = [FIFOScheduler(switch_cost)] + [RoundRobinScheduler(q, switch_cost) for q in quanta]
    results = [scheduler.schedule(workload) for scheduler in schedulers]

    print(render_workload(workload), end="\n\n")
    print(render_comparison(results))
    if "--json" in options:
        print(f"\nJSON-порівняння збережено: {save_comparison_json(results, str(options['--json']))}")
    if "--csv" in options:
        print(f"CSV-порівняння збережено:  {save_comparison_csv(results, str(options['--csv']))}")


def _cmd_benchmark(options: dict) -> None:
    sizes = _int_list(options, "--sizes", "100,1000,10000")
    quantum = _int_option(options, "--quantum", 4, SchedulerConfigError)
    repeats = _int_option(options, "--repeats", 3, SchedulerConfigError)
    rows = run_benchmark(sizes, quantum=quantum, repeats=repeats)

    print(f"{'n':>8}{'алгоритм':>10}{'t, с':>12}{'квантів':>10}")
    for row in rows:
        print(f"{row['n']:>8}{row['algorithm']:>10}{row['seconds']:>12.6f}{row['slices']:>10}")
    if len(sizes) >= 2:
        for name in ("FIFO", "RR"):
            subset = [r for r in rows if r["algorithm"] == name]
            k = estimate_exponent([r["n"] for r in subset], [r["seconds"] for r in subset])
            print(f"Емпіричний показник {name}: t ~ n^{k:.2f}")
    if "--csv" in options:
        import csv
        target = Path(str(options["--csv"]))
        try:
            os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["n", "algorithm", "seconds", "slices"])
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            raise ReportWriteError(f"Не вдалося записати {str(target)!r}: {exc}") from exc
        print(f"CSV збережено: {target}")


def _cmd_generate(options: dict) -> None:
    count = _int_option(options, "--count", None, CliUsageError)
    if count is None:
        raise CliUsageError("Обов'язковий параметр --count не вказано.")
    seed = _int_option(options, "--seed", 1, CliUsageError)
    target = Path(_require(options, "--output"))
    workload = generate_workload(count, seed=seed)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(workload_to_text(workload))
    except OSError as exc:
        raise ReportWriteError(f"Не вдалося записати {str(target)!r}: {exc}") from exc
    print(f"Створено навантаження з {count} процесів: {target}")


COMMANDS = {"run": _cmd_run, "compare": _cmd_compare, "benchmark": _cmd_benchmark,
            "generate": _cmd_generate}

# Порядок важливий: специфічніші винятки - раніше за базові
EXIT_CODES = [(CliUsageError, 1), (WorkloadReadError, 2), (InputFormatError, 2),
              (SchedulerConfigError, 3), (ProcessParameterError, 3), (SimulationError, 4),
              (StorageError, 5), (SchedulerError, 6)]


def exit_code_for(error: Exception) -> int:
    """Код завершення процесу для виняткової ситуації."""
    for error_type, code in EXIT_CODES:
        if isinstance(error, error_type):
            return code
    return 70


def main(argv: list[str] | None = None) -> int:
    """Точка входу: argv[0] - ім'я програми, argv[1] - команда, далі - параметри."""
    argv = list(sys.argv if argv is None else argv)
    if len(argv) <= 1 or argv[1] in ("--help", "-h"):
        print(USAGE)
        return 0
    if argv[1] == "--version":
        print(f"cpu_scheduler {__version__}")
        return 0

    command = argv[1]
    try:
        if command not in COMMANDS:
            raise CliUsageError(f"Невідома команда {command!r}; доступні: {', '.join(COMMANDS)}.")
        options = parse_options(argv[2:], COMMAND_SPECS[command])
        COMMANDS[command](options)
    except SchedulerError as exc:
        print(f"Помилка: {exc}", file=sys.stderr)
        if exc.__cause__ is not None:
            print(f"  причина: {exc.__cause__!r}", file=sys.stderr)
        if isinstance(exc, CliUsageError):
            print("Довідка: python cli_main.py --help", file=sys.stderr)
        return exit_code_for(exc)
    except Exception as exc:                      # непередбачений збій: не губимо трасування
        print(f"Внутрішня помилка: {exc!r}", file=sys.stderr)
        return 70
    return 0
