"""
РГР. Модуль exceptions: ієрархія користувацьких винятків симулятора диспетчера CPU.

Дерево винятків:
    SchedulerError                      (базовий доменний виняток, 1xxx)
    ├── ProcessParameterError           (параметри процесу, 2xxx)
    │   ├── InvalidArrivalError
    │   └── InvalidBurstError
    ├── InputFormatError                (формат вхідних даних, 3xxx)
    │   ├── InvalidLineSyntaxError
    │   ├── DuplicateProcessError
    │   └── EmptyWorkloadError
    ├── SchedulerConfigError            (налаштування алгоритмів, 4xxx)
    │   ├── InvalidQuantumError
    │   ├── InvalidSwitchCostError
    │   └── UnknownAlgorithmError
    ├── SimulationError                 (збої під час симуляції, 5xxx)
    │   └── SimulationLimitExceededError
    ├── StorageError                    (файлове введення-виведення, 6xxx)
    │   ├── ReportWriteError
    │   ├── ReportReadError
    │   └── WorkloadReadError
    └── CliUsageError                   (синтаксис командного рядка, 7xxx)

Усі класи наслідуються від Exception (а не від BaseException), щоб блоки except
не перехоплювали системні сигнали KeyboardInterrupt та SystemExit.
Освітній компонент: Програмування на Python.
"""

__all__ = [
    "SchedulerError", "ProcessParameterError", "InvalidArrivalError", "InvalidBurstError",
    "InputFormatError", "InvalidLineSyntaxError", "DuplicateProcessError", "EmptyWorkloadError",
    "SchedulerConfigError", "InvalidQuantumError", "InvalidSwitchCostError",
    "UnknownAlgorithmError", "SimulationError", "SimulationLimitExceededError",
    "StorageError", "ReportWriteError", "ReportReadError", "WorkloadReadError",
    "CliUsageError",
]


class SchedulerError(Exception):
    """Базовий клас усіх винятків пакета; зберігає числовий код помилки."""

    default_code = 1000

    def __init__(self, message: str, error_code: int | None = None):
        super().__init__(message)
        self.error_code = self.default_code if error_code is None else error_code

    def __str__(self) -> str:
        return f"[SCHED-ERR-{self.error_code}] {super().__str__()}"


# --- Параметри процесу (2xxx) -------------------------------------------------------------

class ProcessParameterError(SchedulerError):
    """Некоректне значення атрибута процесу (тип, діапазон)."""
    default_code = 2000


class InvalidArrivalError(ProcessParameterError):
    """Час надходження не є цілим невід'ємним числом."""
    default_code = 2001


class InvalidBurstError(ProcessParameterError):
    """Тривалість виконання не є цілим додатним числом."""
    default_code = 2002


# --- Формат вхідних даних (3xxx) ----------------------------------------------------------

class InputFormatError(SchedulerError):
    """Помилка структури вхідного файлу робочого навантаження."""
    default_code = 3000


class InvalidLineSyntaxError(InputFormatError):
    """Рядок не відповідає жодному з дозволених шаблонів регулярних виразів."""
    default_code = 3001

    def __init__(self, line_no: int, line: str):
        self.line_no = line_no
        self.line = line
        super().__init__(f"Рядок {line_no} має неприпустимий синтаксис: {line!r}.")


class DuplicateProcessError(InputFormatError):
    """Ідентифікатор процесу повторюється у наборі."""
    default_code = 3002

    def __init__(self, pid: str):
        self.pid = pid
        super().__init__(f"Ідентифікатор процесу {pid!r} уже зареєстровано.")


class EmptyWorkloadError(InputFormatError):
    """Робоче навантаження не містить жодного процесу."""
    default_code = 3003

    def __init__(self, message: str = "Робоче навантаження порожнє: немає жодного процесу."):
        super().__init__(message)


# --- Налаштування алгоритмів (4xxx) -------------------------------------------------------

class SchedulerConfigError(SchedulerError):
    """Некоректні параметри конфігурації планувальника."""
    default_code = 4000


class InvalidQuantumError(SchedulerConfigError):
    """Квант часу Round Robin не є цілим додатним числом."""
    default_code = 4001


class InvalidSwitchCostError(SchedulerConfigError):
    """Вартість перемикання контексту не є цілим невід'ємним числом."""
    default_code = 4002


class UnknownAlgorithmError(SchedulerConfigError):
    """Запитано алгоритм, якого немає у реєстрі."""
    default_code = 4003


# --- Симуляція (5xxx) ---------------------------------------------------------------------

class SimulationError(SchedulerError):
    """Збій у ході симуляції."""
    default_code = 5000


class SimulationLimitExceededError(SimulationError):
    """Перевищено ліміт кроків симуляції (захист від надмірно довгих прогонів)."""
    default_code = 5001

    def __init__(self, limit: int):
        self.limit = limit
        super().__init__(f"Перевищено ліміт {limit} інтервалів виконання; "
                         f"збільште квант часу або ліміт.")


# --- Сховище (6xxx) -----------------------------------------------------------------------

class StorageError(SchedulerError):
    """Помилка читання/запису файлів звітів."""
    default_code = 6000


class ReportWriteError(StorageError):
    """Не вдалося записати файл звіту."""
    default_code = 6001


class ReportReadError(StorageError):
    """Не вдалося прочитати або розібрати файл звіту."""
    default_code = 6002


class WorkloadReadError(StorageError):
    """Не вдалося відкрити або прочитати вхідний файл робочого навантаження."""
    default_code = 6003


# --- Командний рядок (7xxx) ---------------------------------------------------------------

class CliUsageError(SchedulerError):
    """Неправильний синтаксис аргументів командного рядка."""
    default_code = 7001
