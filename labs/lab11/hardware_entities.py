"""
Лабораторна робота № 11. Модуль 1. Варіант 2.
Об'єктно-орієнтована модель процесорного ядра: базовий клас CPUKernel (тактова
частота, IPC) та похідний клас SIMDKernel (розрядність векторного регістра).
Інкапсуляція через @property/@setter, наслідування через super() та
перевантаження dunder-методів: __str__, __repr__, __eq__, __lt__, __add__,
__radd__, __len__, __getitem__.

Модель продуктивності (пікова, одинарна точність FP32):
    P [MFLOPS] = f [ГГц] * 1000 * IPC * L,   L = 1 для скалярного ядра,
                                              L = W / 32 для SIMD-ядра шириною W біт
Семантика операторів варіанта 2:
    a + b  - сумування продуктивності ядер (MFLOPS); результат - нове зведене ядро
    a < b  - порівняння за тактовою частотою

Освітній компонент: Програмування на Python.
"""

import math
from typing import List, Optional, Union

# Інженерні межі параметрів
CLOCK_MIN_GHZ, CLOCK_MAX_GHZ = 0.1, 8.0
# Верхня межа IPC дозволяє також ефективні значення зведених ядер (результат a + b)
IPC_MIN, IPC_MAX = 0.1, 1024.0
ALLOWED_SIMD_WIDTHS = (128, 256, 512)     # допустима розрядність векторного регістра, біт
FP32_LANE_BITS = 32                       # ширина однієї смуги FP32, біт
MFLOPS_PER_GHZ = 1000.0                   # 1 ГГц = 1000 МГц = 1000 млн операцій за секунду


def _require_number(value: object, name: str) -> float:
    """Перевіряє, що value є числом (bool відкидається, бо є підкласом int), і повертає float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} повинна бути числовим значенням, отримано {type(value).__name__}.")
    return float(value)


class CPUKernel:
    """Базовий клас процесорного ядра: ідентифікатор, тактова частота, IPC, телеметрія навантаження."""

    def __init__(self, kernel_id: str, clock_frequency_ghz: float, ipc: float,
                 initial_load_history: Optional[List[float]] = None):
        name = str(kernel_id).strip()
        if not name:
            raise ValueError("Ідентифікатор ядра не може бути порожнім.")

        # Приватні атрибути: компілятор перейменовує їх у _CPUKernel__<ім'я> (name mangling)
        self.__kernel_id: str = name
        self.__clock_frequency_ghz: float = CLOCK_MIN_GHZ
        self.__ipc: float = IPC_MIN
        self.__load_history: List[float] = []

        # Ініціалізація через сетери запускає валідацію інваріантів уже в конструкторі
        self.clock_frequency_ghz = clock_frequency_ghz
        self.ipc = ipc
        for sample in (initial_load_history or []):
            self.record_load(sample)

    # --- Властивості (інкапсуляція) ---

    @property
    def kernel_id(self) -> str:
        """Ідентифікатор ядра (лише читання: сетера немає)."""
        return self.__kernel_id

    @property
    def clock_frequency_ghz(self) -> float:
        """Гетер тактової частоти, ГГц."""
        return self.__clock_frequency_ghz

    @clock_frequency_ghz.setter
    def clock_frequency_ghz(self, value: float) -> None:
        """Сетер тактової частоти з перевіркою типу та інженерних меж."""
        freq = _require_number(value, "Тактова частота")
        if not (CLOCK_MIN_GHZ <= freq <= CLOCK_MAX_GHZ):
            raise ValueError(f"Тактова частота {freq} ГГц поза діапазоном "
                             f"[{CLOCK_MIN_GHZ}; {CLOCK_MAX_GHZ}] ГГц.")
        self.__clock_frequency_ghz = freq

    @property
    def ipc(self) -> float:
        """Гетер IPC (кількість інструкцій за такт)."""
        return self.__ipc

    @ipc.setter
    def ipc(self, value: float) -> None:
        """Сетер IPC з перевіркою типу та меж."""
        ipc_value = _require_number(value, "IPC")
        if not (IPC_MIN <= ipc_value <= IPC_MAX):
            raise ValueError(f"IPC {ipc_value} поза діапазоном [{IPC_MIN}; {IPC_MAX}].")
        self.__ipc = ipc_value

    @property
    def performance_mflops(self) -> float:
        """Обчислювана властивість: пікова продуктивність скалярного ядра, MFLOPS."""
        return self.__clock_frequency_ghz * MFLOPS_PER_GHZ * self.__ipc

    @property
    def average_load_percent(self) -> float:
        """Середнє навантаження за накопиченою телеметрією, %."""
        if not self.__load_history:
            return 0.0
        return sum(self.__load_history) / len(self.__load_history)

    def record_load(self, load_percent: float) -> None:
        """Додає відлік навантаження (0..100 %) до внутрішнього буфера телеметрії."""
        load = _require_number(load_percent, "Навантаження")
        if not (0.0 <= load <= 100.0):
            raise ValueError(f"Навантаження {load} % поза діапазоном [0; 100].")
        self.__load_history.append(load)

    # --- Протокол послідовностей: об'єкт поводиться як колекція відліків телеметрії ---

    def __len__(self) -> int:
        """Кількість відліків у буфері: len(core)."""
        return len(self.__load_history)

    def __getitem__(self, index: Union[int, slice]) -> Union[float, List[float]]:
        """Індексація core[i] та зрізи core[a:b] делегуються внутрішньому списку."""
        return self.__load_history[index]

    # --- Представлення ---

    def __repr__(self) -> str:
        """Однозначний технічний рядок: за ним об'єкт можна відтворити."""
        return (f"CPUKernel(kernel_id={self.__kernel_id!r}, "
                f"clock_frequency_ghz={self.__clock_frequency_ghz}, ipc={self.__ipc}, "
                f"initial_load_history={self.__load_history})")

    def __str__(self) -> str:
        """Форматований рядок для інженерних звітів."""
        return (f"CPU [{self.kernel_id}] | {self.clock_frequency_ghz:.2f} ГГц | "
                f"IPC {self.ipc:.3f} | {self.performance_mflops:.0f} MFLOPS | "
                f"Відліків: {len(self)}")

    # --- Порівняння ---

    def __eq__(self, other: object) -> bool:
        """
        Рівність: однакові клас, ідентифікатор, тактова частота та IPC.
        Перевірка точного класу запобігає рівності CPUKernel та SIMDKernel з однаковими
        базовими параметрами. Для чужих типів повертаємо NotImplemented.
        """
        if not isinstance(other, CPUKernel):
            return NotImplemented
        return (type(self) is type(other)
                and self.kernel_id == other.kernel_id
                and math.isclose(self.clock_frequency_ghz, other.clock_frequency_ghz, rel_tol=1e-9)
                and math.isclose(self.ipc, other.ipc, rel_tol=1e-9))

    def __lt__(self, other: "CPUKernel") -> bool:
        """Критерій варіанта 2: «менше» означає меншу тактову частоту."""
        if not isinstance(other, CPUKernel):
            return NotImplemented
        return self.clock_frequency_ghz < other.clock_frequency_ghz

    # --- Арифметика: сумування продуктивності ---

    def __add__(self, other: "CPUKernel") -> "CPUKernel":
        """
        Сумування продуктивності ядер: повертає нове зведене ядро, продуктивність якого
        дорівнює P1 + P2. Тактова частота зведеного ядра - максимальна з двох, а ефективний
        IPC підбирається так, щоб P = f * 1000 * IPC збігалося із сумою. Буфери телеметрії
        конкатенуються. Операнди не змінюються.
        """
        if not isinstance(other, CPUKernel):
            return NotImplemented     # PVM спробує other.__radd__, а потім згенерує TypeError

        total_mflops = self.performance_mflops + other.performance_mflops
        merged_clock = max(self.clock_frequency_ghz, other.clock_frequency_ghz)
        effective_ipc = total_mflops / (merged_clock * MFLOPS_PER_GHZ)

        return CPUKernel(
            kernel_id=f"{self.kernel_id}+{other.kernel_id}",
            clock_frequency_ghz=merged_clock,
            ipc=effective_ipc,
            initial_load_history=self.__load_history + other.__load_history,
        )

    def __radd__(self, other: object) -> "CPUKernel":
        """
        Реверсивне додавання: потрібне вбудованій sum(), яка починає з 0 (0 + core).
        Для нуля повертаємо саме ядро, для інших типів - NotImplemented.
        """
        if isinstance(other, int) and not isinstance(other, bool) and other == 0:
            return self
        return NotImplemented


class SIMDKernel(CPUKernel):
    """Похідний клас: векторний прискорювач із розрядністю SIMD-регістра."""

    def __init__(self, kernel_id: str, clock_frequency_ghz: float, ipc: float,
                 simd_width_bits: int, initial_load_history: Optional[List[float]] = None):
        # Делегування ініціалізації спільної частини базовому класу
        super().__init__(kernel_id, clock_frequency_ghz, ipc, initial_load_history)
        self.__simd_width_bits: int = ALLOWED_SIMD_WIDTHS[0]
        self.simd_width_bits = simd_width_bits

    @property
    def simd_width_bits(self) -> int:
        """Розрядність векторного регістра, біт."""
        return self.__simd_width_bits

    @simd_width_bits.setter
    def simd_width_bits(self, value: int) -> None:
        """Сетер розрядності: допустимі лише 128, 256 та 512 біт."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("Розрядність SIMD повинна бути цілим числом.")
        if value not in ALLOWED_SIMD_WIDTHS:
            raise ValueError(f"Розрядність {value} біт не підтримується: допустимі {ALLOWED_SIMD_WIDTHS}.")
        self.__simd_width_bits = value

    @property
    def vector_lanes(self) -> int:
        """Кількість смуг FP32 у векторному регістрі: L = W / 32."""
        return self.__simd_width_bits // FP32_LANE_BITS

    @property
    def performance_mflops(self) -> float:
        """Поліморфне перевизначення: скалярна продуктивність, помножена на кількість смуг."""
        return super().performance_mflops * self.vector_lanes

    def __repr__(self) -> str:
        """Технічний рядок похідного класу (перевизначає базовий)."""
        return (f"SIMDKernel(kernel_id={self.kernel_id!r}, "
                f"clock_frequency_ghz={self.clock_frequency_ghz}, ipc={self.ipc}, "
                f"simd_width_bits={self.__simd_width_bits}, "
                f"initial_load_history={self[:]})")

    def __str__(self) -> str:
        """Розширений звіт: базовий рядок плюс параметри векторного блоку."""
        return f"{super().__str__()} | SIMD: {self.__simd_width_bits} біт ({self.vector_lanes} смуг)"

    def __eq__(self, other: object) -> bool:
        """Рівність враховує також розрядність SIMD."""
        base_result = super().__eq__(other)
        if base_result is NotImplemented or not base_result:
            return base_result
        return self.simd_width_bits == other.simd_width_bits
