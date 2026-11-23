"""
РГР. Модуль models: предметні класи симулятора диспетчера CPU.

Класи:
    Process        - вхідний процес (pid, час надходження, тривалість), інкапсуляція через @property;
    Workload       - колекція процесів: протоколи послідовності та оператор + (злиття наборів);
    Segment        - інтервал на діаграмі Ганта (виконання RUN, простій IDLE, перемикання CS);
    ProcessResult  - результат для одного процесу та похідні показники;
    ScheduleResult - результат симуляції: інтервали, показники, порівняння за середнім очікуванням.

Усі часові величини - цілі числа в умовних одиницях (мс).
Освітній компонент: Програмування на Python.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

from .exceptions import (DuplicateProcessError, InvalidArrivalError, InvalidBurstError,
                         ProcessParameterError)

__all__ = ["Process", "Workload", "Segment", "ProcessResult", "ScheduleResult",
           "KIND_RUN", "KIND_IDLE", "KIND_SWITCH"]

KIND_RUN = "RUN"        # процесор виконує користувацький процес
KIND_IDLE = "IDLE"      # черга готових процесів порожня
KIND_SWITCH = "CS"      # накладні витрати на перемикання контексту

_PID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]{0,15}$")


def _require_int(value: object, error_cls: type[ProcessParameterError], name: str) -> int:
    """Перевіряє, що value є цілим числом (bool відкидається, бо є підкласом int)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise error_cls(f"{name} має бути цілим числом, отримано {type(value).__name__}.")
    return value


class Process:
    """Процес, що надходить до планувальника: ідентифікатор, момент надходження, тривалість."""

    def __init__(self, pid: str, arrival_time: int, burst_time: int):
        normalized = str(pid).strip().upper()
        if not _PID_PATTERN.match(normalized):
            raise ProcessParameterError(
                f"Ідентифікатор {pid!r} неприпустимий: очікується літера та до 15 символів "
                f"[A-Z0-9_-].", error_code=2003)

        # Приватні атрибути: name mangling перейменовує їх у _Process__<ім'я>
        self.__pid: str = normalized
        self.__arrival_time: int = 0
        self.__burst_time: int = 1

        # Присвоєння через сетери запускає валідацію вже в конструкторі
        self.arrival_time = arrival_time
        self.burst_time = burst_time

    # --- Властивості (інкапсуляція) ---

    @property
    def pid(self) -> str:
        """Ідентифікатор процесу (лише читання)."""
        return self.__pid

    @property
    def arrival_time(self) -> int:
        """Момент надходження a_i >= 0."""
        return self.__arrival_time

    @arrival_time.setter
    def arrival_time(self, value: int) -> None:
        value = _require_int(value, InvalidArrivalError, "Час надходження")
        if value < 0:
            raise InvalidArrivalError(f"Час надходження {value} не може бути від'ємним.")
        self.__arrival_time = value

    @property
    def burst_time(self) -> int:
        """Тривалість виконання b_i >= 1."""
        return self.__burst_time

    @burst_time.setter
    def burst_time(self, value: int) -> None:
        value = _require_int(value, InvalidBurstError, "Тривалість виконання")
        if value < 1:
            raise InvalidBurstError(f"Тривалість виконання {value} має бути не меншою за 1.")
        self.__burst_time = value

    # --- Представлення, рівність, порядок ---

    def __repr__(self) -> str:
        return (f"Process(pid={self.__pid!r}, arrival_time={self.__arrival_time}, "
                f"burst_time={self.__burst_time})")

    def __str__(self) -> str:
        return f"{self.pid:<6} надходження={self.arrival_time:>4}  тривалість={self.burst_time:>4}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Process):
            return NotImplemented
        return (self.pid, self.arrival_time, self.burst_time) == \
               (other.pid, other.arrival_time, other.burst_time)

    def __lt__(self, other: Process) -> bool:
        """Природний порядок: за часом надходження, за рівності - за ідентифікатором."""
        if not isinstance(other, Process):
            return NotImplemented
        return (self.arrival_time, self.pid) < (other.arrival_time, other.pid)

    # Об'єкт змінюваний (є сетери), тому за контрактом Python він не хешується.
    __hash__ = None  # type: ignore[assignment]


class Workload:
    """Робоче навантаження: впорядкована колекція процесів з унікальними ідентифікаторами."""

    def __init__(self, processes: list[Process] | None = None):
        self.__processes: list[Process] = []
        self.__index: dict[str, Process] = {}
        for process in (processes or []):
            self.add(process)

    def add(self, process: Process) -> None:
        """Додає процес; повторний pid спричиняє DuplicateProcessError."""
        if process.pid in self.__index:
            raise DuplicateProcessError(process.pid)
        self.__processes.append(process)
        self.__index[process.pid] = process

    @property
    def total_burst(self) -> int:
        """Сумарна тривалість B = sum(b_i)."""
        return sum(p.burst_time for p in self.__processes)

    @property
    def earliest_arrival(self) -> int:
        """Мінімальний момент надходження t0 (0 для порожнього набору)."""
        return min((p.arrival_time for p in self.__processes), default=0)

    # --- Протокол послідовності ---

    def __len__(self) -> int:
        return len(self.__processes)

    def __iter__(self) -> Iterator[Process]:
        return iter(self.__processes)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            return item.strip().upper() in self.__index
        return item in self.__processes

    def __getitem__(self, key: int | slice | str) -> Process | list[Process]:
        """workload[i], workload[a:b] та workload['P1']."""
        if isinstance(key, str):
            try:
                return self.__index[key.strip().upper()]
            except KeyError:
                raise KeyError(f"Процес {key!r} відсутній у навантаженні.") from None
        return self.__processes[key]

    # --- Оператор + : злиття двох наборів у новий ---

    def __add__(self, other: object) -> Workload:
        if not isinstance(other, Workload):
            return NotImplemented
        return Workload(list(self) + list(other))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Workload):
            return NotImplemented
        return list(self) == list(other)

    def __repr__(self) -> str:
        return f"Workload({self.__processes!r})"

    def __str__(self) -> str:
        head = f"Робоче навантаження: {len(self)} процесів, B = {self.total_burst}"
        return "\n".join([head] + [f"  {p}" for p in self.__processes])

    __hash__ = None  # type: ignore[assignment]


@dataclass(frozen=True)
class Segment:
    """Інтервал [start, end) на діаграмі Ганта."""

    kind: str          # KIND_RUN, KIND_IDLE або KIND_SWITCH
    pid: str | None    # ідентифікатор для RUN; для CS - процес, на який перемикаються
    start: int
    end: int

    @property
    def duration(self) -> int:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {"kind": self.kind, "pid": self.pid, "start": self.start, "end": self.end}


@dataclass(frozen=True)
class ProcessResult:
    """Підсумок для одного процесу: a_i, b_i, s_i (перший запуск), C_i (завершення)."""

    pid: str
    arrival: int
    burst: int
    first_start: int
    completion: int

    @property
    def turnaround(self) -> int:
        """Час обороту T_i = C_i - a_i."""
        return self.completion - self.arrival

    @property
    def waiting(self) -> int:
        """Час очікування W_i = T_i - b_i."""
        return self.turnaround - self.burst

    @property
    def response(self) -> int:
        """Час відгуку R_i = s_i - a_i."""
        return self.first_start - self.arrival

    @property
    def slowdown(self) -> float:
        """Нормований час обороту T_i / b_i."""
        return self.turnaround / self.burst

    def to_dict(self) -> dict:
        return {"pid": self.pid, "arrival": self.arrival, "burst": self.burst,
                "first_start": self.first_start, "completion": self.completion,
                "turnaround": self.turnaround, "waiting": self.waiting,
                "response": self.response}


class ScheduleResult:
    """Результат одного прогону планувальника: інтервали, результати процесів, показники."""

    def __init__(self, algorithm: str, parameters: dict, processes: list[ProcessResult],
                 segments: list[Segment], context_switches: int, slices: int):
        self.__algorithm = algorithm
        self.__parameters = dict(parameters)
        self.__processes = list(processes)
        self.__segments = list(segments)
        self.__context_switches = context_switches
        self.__slices = slices

    # --- Вихідні дані ---

    @property
    def algorithm(self) -> str:
        return self.__algorithm

    @property
    def parameters(self) -> dict:
        return dict(self.__parameters)

    @property
    def processes(self) -> list[ProcessResult]:
        return list(self.__processes)

    @property
    def segments(self) -> list[Segment]:
        return list(self.__segments)

    @property
    def context_switches(self) -> int:
        return self.__context_switches

    @property
    def slices(self) -> int:
        """Кількість квантів (запусків процесу на процесорі) до злиття суміжних інтервалів."""
        return self.__slices

    @property
    def label(self) -> str:
        """Короткий підпис алгоритму, наприклад 'RR(q=4)' або 'FIFO'."""
        if "quantum" in self.__parameters:
            return f"{self.__algorithm}(q={self.__parameters['quantum']})"
        return self.__algorithm

    # --- Агреговані показники ---

    def _mean(self, attr: str) -> float:
        return sum(getattr(p, attr) for p in self.__processes) / len(self.__processes)

    @property
    def avg_waiting(self) -> float:
        return self._mean("waiting")

    @property
    def avg_turnaround(self) -> float:
        return self._mean("turnaround")

    @property
    def avg_response(self) -> float:
        return self._mean("response")

    @property
    def avg_slowdown(self) -> float:
        return self._mean("slowdown")

    @property
    def max_waiting(self) -> int:
        return max(p.waiting for p in self.__processes)

    @property
    def start_time(self) -> int:
        """t0 - момент початку спостереження (мінімальне надходження)."""
        return min(p.arrival for p in self.__processes)

    @property
    def end_time(self) -> int:
        """L - момент завершення останнього процесу."""
        return max(p.completion for p in self.__processes)

    @property
    def makespan(self) -> int:
        """Довжина інтервалу спостереження L - t0."""
        return self.end_time - self.start_time

    @property
    def busy_time(self) -> int:
        return sum(s.duration for s in self.__segments if s.kind == KIND_RUN)

    @property
    def idle_time(self) -> int:
        return sum(s.duration for s in self.__segments if s.kind == KIND_IDLE)

    @property
    def switch_time(self) -> int:
        return sum(s.duration for s in self.__segments if s.kind == KIND_SWITCH)

    @property
    def utilization(self) -> float:
        """Завантаження CPU U = sum(b_i) / (L - t0), у відсотках."""
        return 100.0 * self.busy_time / self.makespan

    @property
    def throughput(self) -> float:
        """Пропускна здатність: процесів на одиницю часу."""
        return len(self.__processes) / self.makespan

    def summary(self) -> dict:
        """Словник агрегованих показників (рядок порівняльної таблиці)."""
        return {
            "algorithm": self.label,
            "avg_waiting": round(self.avg_waiting, 4),
            "avg_turnaround": round(self.avg_turnaround, 4),
            "avg_response": round(self.avg_response, 4),
            "avg_slowdown": round(self.avg_slowdown, 4),
            "max_waiting": self.max_waiting,
            "makespan": self.makespan,
            "utilization_percent": round(self.utilization, 4),
            "throughput": round(self.throughput, 6),
            "context_switches": self.context_switches,
            "idle_time": self.idle_time,
            "switch_time": self.switch_time,
        }

    def to_dict(self) -> dict:
        return {"algorithm": self.__algorithm, "parameters": self.parameters,
                "metrics": self.summary(),
                "processes": [p.to_dict() for p in self.__processes],
                "segments": [s.to_dict() for s in self.__segments]}

    # --- Dunder-методи ---

    def __len__(self) -> int:
        return len(self.__processes)

    def __iter__(self) -> Iterator[ProcessResult]:
        return iter(self.__processes)

    def __getitem__(self, key: int | str) -> ProcessResult:
        if isinstance(key, str):
            for item in self.__processes:
                if item.pid == key.strip().upper():
                    return item
            raise KeyError(f"Процес {key!r} відсутній у результаті.")
        return self.__processes[key]

    def __lt__(self, other: ScheduleResult) -> bool:
        """a < b <=> середній час очікування a менший: min(results) дає найкращий алгоритм."""
        if not isinstance(other, ScheduleResult):
            return NotImplemented
        return self.avg_waiting < other.avg_waiting

    def __repr__(self) -> str:
        return (f"ScheduleResult({self.label}, processes={len(self)}, "
                f"avg_waiting={self.avg_waiting:.3f})")

    def __str__(self) -> str:
        return (f"{self.label}: W={self.avg_waiting:.2f}  T={self.avg_turnaround:.2f}  "
                f"R={self.avg_response:.2f}  U={self.utilization:.1f}%  CS={self.context_switches}")
