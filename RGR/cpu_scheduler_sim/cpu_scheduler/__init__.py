"""
Пакет cpu_scheduler - симулятор диспетчеризації черги завдань процесора (FIFO, Round Robin).
Розрахунково-графічна робота з дисципліни «Програмування на Python. Базовий рівень».
"""

__version__ = "1.0.0"

from .benchmark import estimate_exponent, generate_workload, run_benchmark, time_scheduler  # noqa: F401
from .exceptions import *            # noqa: F401,F403  (список експорту визначено в exceptions.__all__)
from .exceptions import __all__ as _exception_names
from .models import ProcessResult, Process, ScheduleResult, Segment, Workload  # noqa: F401
from .parser import load_workload, parse_workload_text  # noqa: F401
from .reporting import render_comparison, render_gantt, render_summary, render_table  # noqa: F401
from .schedulers import BaseScheduler, FIFOScheduler, RoundRobinScheduler, create_scheduler  # noqa: F401
from .storage import load_json, save_comparison_csv, save_csv, save_json  # noqa: F401

# Суворий публічний інтерфейс пакета; внутрішні класи (_Timeline) та функції назовні не експортуються
__all__ = [
    "__version__", "Process", "Workload", "Segment", "ProcessResult", "ScheduleResult",
    "BaseScheduler", "FIFOScheduler", "RoundRobinScheduler", "create_scheduler",
    "load_workload", "parse_workload_text", "save_json", "load_json", "save_csv",
    "save_comparison_csv", "render_table", "render_summary", "render_gantt",
    "render_comparison", "generate_workload", "run_benchmark", "time_scheduler",
    "estimate_exponent",
] + list(_exception_names)
