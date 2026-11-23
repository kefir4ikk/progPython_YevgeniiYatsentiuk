"""
РГР. Модуль schedulers: алгоритми диспетчеризації FIFO (FCFS) та Round Robin.

Архітектура (шаблонний метод + поліморфізм):
    BaseScheduler (ABC)      - валідація, спільний цикл schedule(), метод _dispatch() перевизначається;
    ├── FIFOScheduler        - без витіснення, порядок надходження;
    └── RoundRobinScheduler  - кругова черга з квантом часу q.
    _Timeline                - внутрішній «годинник»: накопичує інтервали Ганта та моменти подій.

Угоди моделі (однакові для всіх алгоритмів):
    1) Годинник стартує в момент найранішого надходження t0.
    2) Якщо черга готових порожня, процесор простоює (IDLE) до наступного надходження.
    3) Перемикання контексту між двома різними процесами коштує sigma одиниць часу; перемикання
       після простою вважається безкоштовним. Кожна зміна процесу рахується як перемикання.
    4) Round Robin: процеси, що надійшли до завершення кванта (включно з його кінцем), стають
       у чергу РАНІШЕ за витіснений процес.
Освітній компонент: Програмування на Python.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque

from .exceptions import (EmptyWorkloadError, InvalidQuantumError, InvalidSwitchCostError,
                         SchedulerConfigError, SimulationLimitExceededError, UnknownAlgorithmError)
from .models import (KIND_IDLE, KIND_RUN, KIND_SWITCH, ProcessResult, ScheduleResult, Segment,
                     Workload)

__all__ = ["BaseScheduler", "FIFOScheduler", "RoundRobinScheduler", "create_scheduler",
           "ALGORITHMS", "DEFAULT_MAX_SLICES"]

DEFAULT_MAX_SLICES = 5_000_000   # захист від надмірно довгих прогонів (кванти)


def _require_int(value: object, error_cls: type[Exception], name: str, minimum: int) -> int:
    """Перевіряє тип (не bool) і нижню межу цілого параметра конфігурації."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise error_cls(f"{name} має бути цілим числом, отримано {type(value).__name__}.")
    if value < minimum:
        raise error_cls(f"{name} = {value} менше допустимого мінімуму {minimum}.")
    return value


class _Timeline:
    """Годинник симуляції: єдине місце, де змінюються час, список інтервалів і лічильники."""

    def __init__(self, start_time: int, switch_cost: int, max_slices: int):
        self.clock = start_time
        self.segments: list[Segment] = []
        self.first_start: dict[str, int] = {}
        self.completion: dict[str, int] = {}
        self.context_switches = 0
        self.slices = 0
        self._last_pid: str | None = None
        self._switch_cost = switch_cost
        self._max_slices = max_slices

    def idle_until(self, moment: int) -> None:
        """Простій до моменту moment (якщо він у майбутньому); після простою перемикання безкоштовне."""
        if moment > self.clock:
            self.segments.append(Segment(KIND_IDLE, None, self.clock, moment))
            self.clock = moment
        self._last_pid = None

    def run(self, pid: str, duration: int) -> None:
        """Виконує pid протягом duration; за потреби спершу оплачує перемикання контексту."""
        if self._last_pid is not None and self._last_pid != pid:
            self.context_switches += 1
            if self._switch_cost > 0:
                self.segments.append(
                    Segment(KIND_SWITCH, pid, self.clock, self.clock + self._switch_cost))
                self.clock += self._switch_cost

        self.slices += 1
        if self.slices > self._max_slices:
            raise SimulationLimitExceededError(self._max_slices)

        self.first_start.setdefault(pid, self.clock)
        end = self.clock + duration
        last = self.segments[-1] if self.segments else None
        if last and last.kind == KIND_RUN and last.pid == pid and last.end == self.clock:
            self.segments[-1] = Segment(KIND_RUN, pid, last.start, end)   # злиття суміжних кусків
        else:
            self.segments.append(Segment(KIND_RUN, pid, self.clock, end))
        self.clock = end
        self._last_pid = pid

    def complete(self, pid: str) -> None:
        self.completion[pid] = self.clock


class BaseScheduler(ABC):
    """Абстрактний планувальник: спільна оболонка для FIFO та Round Robin."""

    def __init__(self, switch_cost: int = 0, max_slices: int = DEFAULT_MAX_SLICES):
        self.__switch_cost = 0
        self.__max_slices = DEFAULT_MAX_SLICES
        self.switch_cost = switch_cost
        self.max_slices = max_slices

    @property
    def switch_cost(self) -> int:
        """Вартість перемикання контексту sigma >= 0."""
        return self.__switch_cost

    @switch_cost.setter
    def switch_cost(self, value: int) -> None:
        self.__switch_cost = _require_int(value, InvalidSwitchCostError,
                                          "Вартість перемикання", 0)

    @property
    def max_slices(self) -> int:
        """Ліміт інтервалів виконання за один прогін."""
        return self.__max_slices

    @max_slices.setter
    def max_slices(self, value: int) -> None:
        self.__max_slices = _require_int(value, SchedulerConfigError,
                                         "Ліміт інтервалів", 1)

    @property
    @abstractmethod
    def name(self) -> str:
        """Назва алгоритму для звітів."""

    def parameters(self) -> dict:
        """Параметри конфігурації, що потрапляють у звіт."""
        return {"switch_cost": self.switch_cost}

    @abstractmethod
    def _dispatch(self, workload: Workload, timeline: _Timeline) -> None:
        """Заповнює часову лінію подіями; реалізується в нащадках."""

    def schedule(self, workload: Workload) -> ScheduleResult:
        """Шаблонний метод: перевірка вхідних даних, прогін, збір результату."""
        if len(workload) == 0:
            raise EmptyWorkloadError()
        timeline = _Timeline(workload.earliest_arrival, self.switch_cost, self.max_slices)
        self._dispatch(workload, timeline)
        results = [ProcessResult(p.pid, p.arrival_time, p.burst_time,
                                 timeline.first_start[p.pid], timeline.completion[p.pid])
                   for p in workload]
        return ScheduleResult(self.name, self.parameters(), results, timeline.segments,
                              timeline.context_switches, timeline.slices)

    def __repr__(self) -> str:
        params = ", ".join(f"{k}={v!r}" for k, v in self.parameters().items())
        return f"{type(self).__name__}({params})"


class FIFOScheduler(BaseScheduler):
    """FIFO / FCFS: процеси виконуються до завершення у порядку надходження (без витіснення)."""

    @property
    def name(self) -> str:
        return "FIFO"

    def _dispatch(self, workload: Workload, timeline: _Timeline) -> None:
        # sorted() стабільний: за однакового надходження зберігається порядок у вхідному файлі
        for process in sorted(workload, key=lambda p: p.arrival_time):
            if process.arrival_time > timeline.clock:
                timeline.idle_until(process.arrival_time)
            timeline.run(process.pid, process.burst_time)
            timeline.complete(process.pid)


class RoundRobinScheduler(BaseScheduler):
    """Round Robin: кругова черга, кожен процес отримує не більше q одиниць часу поспіль."""

    def __init__(self, quantum: int, switch_cost: int = 0, max_slices: int = DEFAULT_MAX_SLICES):
        super().__init__(switch_cost, max_slices)
        self.__quantum = 1
        self.quantum = quantum

    @property
    def quantum(self) -> int:
        """Квант часу q >= 1."""
        return self.__quantum

    @quantum.setter
    def quantum(self, value: int) -> None:
        self.__quantum = _require_int(value, InvalidQuantumError, "Квант часу", 1)

    @property
    def name(self) -> str:
        return "RR"

    def parameters(self) -> dict:
        params = super().parameters()
        params["quantum"] = self.quantum
        return params

    def _dispatch(self, workload: Workload, timeline: _Timeline) -> None:
        pending = sorted(workload, key=lambda p: p.arrival_time)     # стабільне впорядкування
        remaining = {p.pid: p.burst_time for p in pending}
        queue: deque[str] = deque()
        admitted = 0                       # індекс першого ще не допущеного до черги процесу
        total = len(pending)
        finished = 0

        def admit_arrived() -> None:
            nonlocal admitted
            while admitted < total and pending[admitted].arrival_time <= timeline.clock:
                queue.append(pending[admitted].pid)
                admitted += 1

        while finished < total:
            admit_arrived()
            if not queue:                  # черга порожня: простій до наступного надходження
                timeline.idle_until(pending[admitted].arrival_time)
                continue
            pid = queue.popleft()
            piece = min(self.quantum, remaining[pid])
            timeline.run(pid, piece)
            remaining[pid] -= piece
            admit_arrived()                # нові процеси - раніше за витіснений (угода 4)
            if remaining[pid] == 0:
                timeline.complete(pid)
                finished += 1
            else:
                queue.append(pid)


ALGORITHMS = {"fifo": FIFOScheduler, "rr": RoundRobinScheduler}


def create_scheduler(name: str, quantum: int | None = None, switch_cost: int = 0,
                     max_slices: int = DEFAULT_MAX_SLICES) -> BaseScheduler:
    """Фабрика за ім'ям алгоритму ('fifo' або 'rr'); для rr обов'язковий quantum."""
    key = str(name).strip().lower()
    if key not in ALGORITHMS:
        raise UnknownAlgorithmError(
            f"Невідомий алгоритм {name!r}; доступні: {', '.join(sorted(ALGORITHMS))}.")
    if key == "fifo":
        return FIFOScheduler(switch_cost, max_slices)
    if quantum is None:
        raise InvalidQuantumError("Для алгоритму rr необхідно вказати квант часу.")
    return RoundRobinScheduler(quantum, switch_cost, max_slices)
