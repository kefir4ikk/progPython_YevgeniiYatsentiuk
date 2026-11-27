"""Об'єктна модель сенсорів комп'ютерної мережі.

Ієрархія класів:

    SerializableMixin ─┐
                       ├─ BaseSensor (ABC)
    ABC ───────────────┘      ├── ThermalSensor ─┬─ TemperatureSensor
                              │                  └─ FanSensor
                              └── VoltageSensor

    CalibratedMixin підмішується до TemperatureSensor і VoltageSensor.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar

from .exceptions import (
    InvalidStatusError,
    UnknownSensorKindError,
    ValueOutOfRangeError,
)
from .flags import (
    CRITICAL_MASK,
    MAX_STATUS,
    StatusFlags,
    decode_flags,
    has_reserved_bits,
    quality_of,
)

__all__ = [
    "SerializableMixin",
    "CalibratedMixin",
    "BaseSensor",
    "ThermalSensor",
    "TemperatureSensor",
    "FanSensor",
    "VoltageSensor",
    "create_sensor",
    "known_kinds",
]

_REGISTRY: dict[str, type["BaseSensor"]] = {}


class SerializableMixin:
    """Домішка: перетворення об'єкта на словник для звітів."""

    __slots__ = ()
    FIELDS: ClassVar[tuple[str, ...]] = ()

    def as_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.FIELDS}


class CalibratedMixin:
    """Домішка: фабрична поправка вимірювача (адитивна)."""

    __slots__ = ()
    CALIBRATION_OFFSET: ClassVar[float] = 0.0

    @property
    def calibrated_value(self) -> float:
        return self.value + self.CALIBRATION_OFFSET  # type: ignore


class BaseSensor(SerializableMixin, ABC):
    """Абстрактний сенсор: загальні дані, перевірки й шаблонний метод."""

    __slots__ = ("_node_id", "_status", "_value", "_timestamp")

    KIND: ClassVar[str] = ""
    UNIT: ClassVar[str] = ""
    VALID_RANGE: ClassVar[tuple[float, float]] = (-math.inf, math.inf)
    FIELDS = ("node_id", "kind", "status", "value", "unit", "timestamp")

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # Реєструємо лише класи, що самі оголосили KIND.
        if cls.__dict__.get("KIND"):
            _REGISTRY[cls.KIND] = cls

    def __init__(self, node_id: str, status: int, value: float,
                 timestamp: datetime) -> None:
        if not node_id.startswith(f"{self.KIND}-"):
            raise ValueError(
                f"{node_id!r} не належить до типу {self.KIND!r}")
        self._node_id = node_id
        self._timestamp = timestamp
        self.status = status   # через сеттер: валідація
        self.value = value     # через сеттер: валідація

    # ---- інкапсульовані властивості --------------------------------
    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def kind(self) -> str:
        return self.KIND

    @property
    def unit(self) -> str:
        return self.UNIT

    @property
    def status(self) -> int:
        return self._status

    @status.setter
    def status(self, new_status: int) -> None:
        if isinstance(new_status, bool) or not isinstance(new_status, int):
            raise InvalidStatusError("регістр стану має бути цілим числом")
        if not 0 <= new_status <= MAX_STATUS:
            raise InvalidStatusError(
                f"регістр {new_status:#x} не вміщується у 16 біт")
        if has_reserved_bits(new_status):
            raise InvalidStatusError(
                f"регістр {new_status:#06x}: зарезервовані біти 8..11 "
                f"не нульові")
        self._status = new_status

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, new_value: float) -> None:
        low, high = self.VALID_RANGE
        if not math.isfinite(new_value) or not low <= new_value <= high:
            raise ValueOutOfRangeError(
                f"значення {new_value} {self.UNIT} поза фізичним "
                f"діапазоном [{low}; {high}] для {self.KIND}")
        self._value = float(new_value)

    # ---- похідні величини ------------------------------------------
    @property
    def quality(self) -> int:
        return quality_of(self._status)

    @property
    def flags(self) -> tuple[StatusFlags, ...]:
        return decode_flags(self._status)

    @property
    def critical_flags(self) -> tuple[StatusFlags, ...]:
        return tuple(f for f in self.flags if int(f) & CRITICAL_MASK)

    @property
    def warning_flags(self) -> tuple[StatusFlags, ...]:
        return tuple(f for f in self.flags if not int(f) & CRITICAL_MASK)

    # ---- шаблонний метод -------------------------------------------
    @abstractmethod
    def check_nominal(self) -> list[str]:
        """Порушення номінальних меж; порожній список, якщо все гаразд."""

    def diagnose(self) -> list[str]:
        """Повний перелік причин критичності: прапорці + межі."""
        reasons = [f"прапорець {flag.name}" for flag in self.critical_flags]
        reasons.extend(self.check_nominal())
        return reasons

    @property
    def is_critical(self) -> bool:
        return bool(self.critical_flags) or bool(self.check_nominal())

    # ---- магічні методи --------------------------------------------
    def _key(self) -> tuple:
        return (self._node_id, self._status, self._value, self._timestamp)

    def __str__(self) -> str:
        return (f"{self._node_id} {self._value:g} {self.UNIT} "
                f"[{self._status:#06x}] {self._timestamp:%Y-%m-%d %H:%M:%S}")

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(node_id={self._node_id!r}, "
                f"status={self._status:#06x}, value={self._value!r}, "
                f"timestamp={self._timestamp!r})")

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self._key() == other._key()  # type: ignore[attr-defined]

    def __hash__(self) -> int:
        # Лише незмінні поля: рівні об'єкти мають однаковий хеш.
        return hash((self.KIND, self._node_id, self._timestamp))


class ThermalSensor(BaseSensor):
    """Проміжний клас для сенсорів системи охолодження."""

    __slots__ = ()

    @property
    def thermal_flags(self) -> int:
        mask = int(StatusFlags.OVER_TEMP | StatusFlags.FAN_FAILURE)
        return self._status & mask


class TemperatureSensor(ThermalSensor, CalibratedMixin):
    """Датчик температури вузла, °C."""

    __slots__ = ()
    KIND = "TMP"
    UNIT = "°C"
    VALID_RANGE = (-55.0, 150.0)
    CALIBRATION_OFFSET = -0.5
    MAX_NOMINAL = 85.0
    MIN_NOMINAL = -10.0

    def check_nominal(self) -> list[str]:
        temp = self.calibrated_value
        if temp > self.MAX_NOMINAL:
            return [f"температура {temp:g} °C (з поправкою) вища за "
                    f"{self.MAX_NOMINAL:g}"]
        if temp < self.MIN_NOMINAL:
            return [f"температура {temp:g} °C (з поправкою) нижча за "
                    f"{self.MIN_NOMINAL:g}"]
        return []


class FanSensor(ThermalSensor):
    """Тахометр вентилятора, об/хв."""

    __slots__ = ()
    KIND = "FAN"
    UNIT = "об/хв"
    VALID_RANGE = (0.0, 20000.0)
    MIN_NOMINAL = 1000.0

    def check_nominal(self) -> list[str]:
        if self._value < self.MIN_NOMINAL:
            return [f"обороти {self._value:g} нижчі за {self.MIN_NOMINAL:g}"]
        return []


class VoltageSensor(BaseSensor, CalibratedMixin):
    """Датчик напруги шини живлення 12 В."""

    __slots__ = ()
    KIND = "VLT"
    UNIT = "В"
    VALID_RANGE = (0.0, 60.0)
    NOMINAL = (11.4, 12.6)

    def check_nominal(self) -> list[str]:
        low, high = self.NOMINAL
        volts = self.calibrated_value
        if not low <= volts <= high:
            return [f"напруга {volts:g} В поза межами {low}..{high}"]
        return []


def known_kinds() -> tuple[str, ...]:
    """Зареєстровані префікси типів сенсорів."""
    return tuple(sorted(_REGISTRY))


def create_sensor(node_id: str, status: int, value: float,
                  timestamp: datetime) -> BaseSensor:
    """Фабрика: тип сенсора визначається префіксом ідентифікатора."""
    kind = node_id.partition("-")[0]
    try:
        cls = _REGISTRY[kind]
    except KeyError:
        raise UnknownSensorKindError(
            f"невідомий тип сенсора {kind!r}; "
            f"допустимі: {', '.join(known_kinds())}") from None
    return cls(node_id, status, value, timestamp)