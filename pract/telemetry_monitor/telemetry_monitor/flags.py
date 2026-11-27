"""Розшифрування 16-бітного регістра стану за допомогою побітової арифметики.

Карта регістра:

    біти 15..12  якість вимірювання (0..15)
    біти 11..8   зарезервовано, мають дорівнювати 0
    біти  7..0   прапорці помилок (див. StatusFlags)
"""

from __future__ import annotations

import enum

__all__ = [
    "StatusFlags",
    "FLAGS_MASK",
    "RESERVED_MASK",
    "CRITICAL_MASK",
    "MAX_STATUS",
    "quality_of",
    "has_reserved_bits",
    "set_bit_positions",
    "popcount",
    "decode_flags",
    "critical_part",
]


class StatusFlags(enum.IntFlag):
    """Апаратні прапорці помилок (молодший байт регістра)."""

    OVER_TEMP = 1 << 0
    UNDER_VOLTAGE = 1 << 1
    OVER_VOLTAGE = 1 << 2
    FAN_FAILURE = 1 << 3
    LINK_DOWN = 1 << 4
    CRC_ERROR = 1 << 5
    SENSOR_FAULT = 1 << 6
    WATCHDOG_RESET = 1 << 7


MAX_STATUS = 0xFFFF
FLAGS_MASK = 0x00FF
RESERVED_MASK = 0x0F00
QUALITY_SHIFT = 12
QUALITY_MASK = 0x0F

# Критичні: перегрів, просідання й перенапруга, відмова вентилятора,
# збій самого сенсора. Решта (LINK_DOWN, CRC_ERROR, WATCHDOG_RESET) —
# попередження.
CRITICAL_MASK = int(
    StatusFlags.OVER_TEMP
    | StatusFlags.UNDER_VOLTAGE
    | StatusFlags.OVER_VOLTAGE
    | StatusFlags.FAN_FAILURE
    | StatusFlags.SENSOR_FAULT
)


def quality_of(status: int) -> int:
    """Старший ніббл: зсув праворуч на 12 і маска 0x0F."""
    return (status >> QUALITY_SHIFT) & QUALITY_MASK


def has_reserved_bits(status: int) -> bool:
    """Чи встановлено хоча б один із зарезервованих бітів 8..11."""
    return bool(status & RESERVED_MASK)


def set_bit_positions(status: int) -> tuple[int, ...]:
    """Номери встановлених бітів прапорців, від молодшого до старшого.

    Прийом ``x & -x`` виділяє наймолодший одиничний біт: у доповняльному
    коді ``-x`` інвертує всі біти зліва від нього, а сам він лишається.
    Операція ``x ^= low`` скидає знайдений біт, тож цикл виконується
    рівно стільки разів, скільки в регістрі одиниць.
    """
    rest = status & FLAGS_MASK
    positions = []
    while rest:
        lowest = rest & -rest
        positions.append(lowest.bit_length() - 1)
        rest ^= lowest
    return tuple(positions)


def popcount(status: int) -> int:
    """Кількість одиничних бітів (алгоритм Брайана Кернігана).

    Вираз ``x & (x - 1)`` скидає наймолодший одиничний біт.
    """
    rest = status & FLAGS_MASK
    count = 0
    while rest:
        rest &= rest - 1
        count += 1
    return count


def decode_flags(status: int) -> tuple[StatusFlags, ...]:
    """Розшифровує регістр у кортеж іменованих прапорців."""
    return tuple(StatusFlags(1 << pos) for pos in set_bit_positions(status))


def critical_part(status: int) -> int:
    """Критичні прапорці регістра: порозрядне «І» з маскою."""
    return status & CRITICAL_MASK