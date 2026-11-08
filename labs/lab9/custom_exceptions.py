"""
Лабораторна робота № 9. Модуль 1. Варіант 2.
Ієрархія користувацьких класів винятків для системи валідації конфігурації
модуля швидкісного аналого-цифрового перетворювача (ADC).

Фізичні обмеження варіанта 2:
    частота вибірки:   1 ... 100 МГц
    вхідна напруга:    -2.5 ... +2.5 В
Додатковий інваріант предметної області: за критерієм Найквіста частота сигналу
повинна бути строго меншою за половину частоти вибірки (f_signal < f_s / 2).

Освітній компонент: Програмування на Python.
"""

import time


class ADCValidationError(Exception):
    """
    Базовий доменний клас для всіх винятків валідації конфігурації АЦП.
    Наслідується від Exception (а не від BaseException), щоб блоки except не
    перехоплювали системні сигнали KeyboardInterrupt та SystemExit.
    """

    def __init__(self, message: str, error_code: int = 2000):
        super().__init__(message)
        self.error_code = error_code
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self) -> str:
        return f"[ADC-ERR-{self.error_code}] ({self.timestamp}) {super().__str__()}"


class SamplingRateError(ADCValidationError):
    """Збуджується, коли частота вибірки виходить за допустимий діапазон АЦП."""

    def __init__(self, rate_mhz: float, min_mhz: float = 1.0, max_mhz: float = 100.0):
        self.rate_mhz = rate_mhz
        self.min_mhz = min_mhz
        self.max_mhz = max_mhz
        msg = (f"Частота вибірки {rate_mhz:.2f} МГц виходить за межі допустимого "
               f"діапазону [{min_mhz:.2f} .. {max_mhz:.2f}] МГц.")
        super().__init__(msg, error_code=2001)


class InputOverloadError(ADCValidationError):
    """Збуджується, коли вхідна напруга перевищує діапазон повної шкали АЦП."""

    def __init__(self, voltage_v: float, min_v: float = -2.5, max_v: float = 2.5):
        self.voltage_v = voltage_v
        self.min_v = min_v
        self.max_v = max_v
        msg = (f"Вхідна напруга {voltage_v:+.2f} В перевантажує вхід АЦП: "
               f"допустимий діапазон [{min_v:+.2f} .. {max_v:+.2f}] В.")
        super().__init__(msg, error_code=2002)


class NyquistViolationError(ADCValidationError):
    """Збуджується, коли частота сигналу не менша за межу Найквіста (f_s / 2)."""

    def __init__(self, signal_freq_mhz: float, sampling_rate_mhz: float):
        self.signal_freq_mhz = signal_freq_mhz
        self.sampling_rate_mhz = sampling_rate_mhz
        self.nyquist_limit_mhz = sampling_rate_mhz / 2.0
        msg = (f"Частота сигналу {signal_freq_mhz:.2f} МГц не менша за межу Найквіста "
               f"{self.nyquist_limit_mhz:.2f} МГц (f_s = {sampling_rate_mhz:.2f} МГц): "
               f"можливе перекриття спектра (aliasing).")
        super().__init__(msg, error_code=2003)
