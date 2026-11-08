"""
Лабораторна робота № 9. Модуль 2. Варіант 2.
Багаторівнева валідація конфігурації модуля швидкісного АЦП (парадигма EAFP),
ланцюжки винятків (raise ... from ...) та тестовий стенд відмовостійкості
з розрахунком коефіцієнта програмного відновлення P_recovery.
Освітній компонент: Програмування на Python.
"""

import time
from typing import Any, Dict

from custom_exceptions import (
    ADCValidationError,
    SamplingRateError,
    InputOverloadError,
    NyquistViolationError,
)

# Фізичні межі варіанта 2
RATE_MIN_MHZ, RATE_MAX_MHZ = 1.0, 100.0
VOLT_MIN_V, VOLT_MAX_V = -2.5, 2.5
REQUIRED_KEYS = {"sampling_rate_mhz", "input_voltage_v"}


def _ensure_within(name: str, value: float, low: float, high: float) -> None:
    """
    Низькорівнева перевірка належності значення діапазону [low, high].
    Генерує стандартний ValueError, який верхні рівні перетворюють
    на доменний виняток із збереженням першопричини (raise ... from ...).
    Для NaN вираз low <= value <= high хибний, тому NaN також відхиляється.
    """
    if not (low <= value <= high):
        raise ValueError(f"{name} = {value} не належить діапазону [{low}, {high}]")


def validate_adc_configuration(config: Dict[str, Any]) -> Dict[str, float]:
    """
    Виконує послідовну валідацію конфігурації АЦП і повертає розраховані характеристики:
    частоту вибірки, вхідну напругу, період вибірки (нс) та смугу Найквіста (МГц).
    Рівні перевірки: структура -> типи -> фізичні межі -> інваріант Найквіста.
    """
    # Рівень 1. Структура: тип контейнера та наявність обов'язкових ключів
    if not isinstance(config, dict):
        raise TypeError(f"Конфігурація повинна бути словником, отримано {type(config).__name__}.")

    missing_keys = REQUIRED_KEYS.difference(config.keys())
    if missing_keys:
        raise KeyError(f"У конфігурації відсутні обов'язкові параметри: {sorted(missing_keys)}")

    # Рівень 2. Типи: EAFP - спершу пробуємо перетворити, помилку обробляємо потім
    try:
        sampling_rate = float(config["sampling_rate_mhz"])
        input_voltage = float(config["input_voltage_v"])
    except (ValueError, TypeError) as conv_err:
        # Ланцюжок винятків: у __cause__ зберігається первинна помилка перетворення
        raise ADCValidationError(
            "Параметри 'sampling_rate_mhz' та 'input_voltage_v' повинні бути числовими.",
            error_code=2004,
        ) from conv_err

    # Рівень 3. Фізичні межі: низькорівневий ValueError перетворюється на доменний виняток
    try:
        _ensure_within("sampling_rate_mhz", sampling_rate, RATE_MIN_MHZ, RATE_MAX_MHZ)
    except ValueError as range_err:
        raise SamplingRateError(sampling_rate, RATE_MIN_MHZ, RATE_MAX_MHZ) from range_err

    try:
        _ensure_within("input_voltage_v", input_voltage, VOLT_MIN_V, VOLT_MAX_V)
    except ValueError as range_err:
        raise InputOverloadError(input_voltage, VOLT_MIN_V, VOLT_MAX_V) from range_err

    # Рівень 4. Інваріант Найквіста (необов'язковий параметр signal_freq_mhz)
    if "signal_freq_mhz" in config:
        try:
            signal_freq = float(config["signal_freq_mhz"])
        except (ValueError, TypeError) as conv_err:
            raise ADCValidationError(
                "Параметр 'signal_freq_mhz' повинен бути числовим.", error_code=2005
            ) from conv_err
        if signal_freq >= sampling_rate / 2.0:
            raise NyquistViolationError(signal_freq, sampling_rate)

    return {
        "sampling_rate_mhz": sampling_rate,
        "input_voltage_v": input_voltage,
        "sample_period_ns": 1000.0 / sampling_rate,
        "nyquist_mhz": sampling_rate / 2.0,
    }


def describe_cause(err: BaseException) -> str:
    """Повертає рядок із першопричиною (__cause__) виняткової ситуації, якщо вона є."""
    cause = err.__cause__
    return f"{type(cause).__name__}: {cause}" if cause is not None else ""


def run_fault_tolerance_testbench(test_configs: list) -> None:
    """
    Запускає тестовий стенд: кожен набір проходить через try-except-else-finally.
    Підраховує успішні конфігурації, локалізовані збої та коефіцієнт відновлення
    P_recovery = N_handled / N_total_faults.
    """
    header_sep = "=" * 90
    sub_sep = "-" * 90

    print(header_sep)
    print(f"{'ТЕСТУВАННЯ ВІДМОВОСТІЙКОСТІ ТА ОБРОБКИ ВИНЯТКІВ МОДУЛЯ АЦП':^90}")
    print(header_sep)

    successful_runs = 0
    handled_faults = 0
    unclassified_faults = 0
    fault_stats: Dict[str, int] = {}
    total_configs = len(test_configs)

    for idx, cfg in enumerate(test_configs, start=1):
        print(f"\nТест #{idx:02d}: конфігурація -> {cfg}")
        try:
            result = validate_adc_configuration(cfg)

        # Порядок except: від найспеціалізованіших нащадків до найзагальніших класів
        except SamplingRateError as err:
            handled_faults += 1
            fault_stats["SamplingRateError"] = fault_stats.get("SamplingRateError", 0) + 1
            print(f"  [ПЕРЕХОПЛЕНО СПЕЦІАЛІЗОВАНО]: {err}")
            safe_rate = max(err.min_mhz, min(err.rate_mhz, err.max_mhz))
            print(f"  -> Дія системи: обмеження частоти вибірки до {safe_rate:.2f} МГц.")
            print(f"  -> Першопричина: {describe_cause(err)}")
        except InputOverloadError as err:
            handled_faults += 1
            fault_stats["InputOverloadError"] = fault_stats.get("InputOverloadError", 0) + 1
            print(f"  [ПЕРЕХОПЛЕНО СПЕЦІАЛІЗОВАНО]: {err}")
            safe_v = max(err.min_v, min(err.voltage_v, err.max_v))
            print(f"  -> Дія системи: увімкнення атенюатора, обмеження входу до {safe_v:+.2f} В.")
            print(f"  -> Першопричина: {describe_cause(err)}")
        except NyquistViolationError as err:
            handled_faults += 1
            fault_stats["NyquistViolationError"] = fault_stats.get("NyquistViolationError", 0) + 1
            print(f"  [ПЕРЕХОПЛЕНО СПЕЦІАЛІЗОВАНО]: {err}")
            need_rate = 2.0 * err.signal_freq_mhz
            print(f"  -> Дія системи: потрібна частота вибірки > {need_rate:.2f} МГц "
                  f"або антиаліасинговий фільтр.")
        except ADCValidationError as err:
            handled_faults += 1
            fault_stats["ADCValidationError"] = fault_stats.get("ADCValidationError", 0) + 1
            print(f"  [ПЕРЕХОПЛЕНО БАЗОВИЙ ДОМЕННИЙ]: {err}")
            print(f"  -> Першопричина (Chained Cause): {describe_cause(err)}")
            print("  -> Дія системи: відхилення конфігурації, збереження попередніх налаштувань.")
        except TypeError as err:
            handled_faults += 1
            fault_stats["TypeError"] = fault_stats.get("TypeError", 0) + 1
            print(f"  [ПЕРЕХОПЛЕНО СТАНДАРТНИЙ TypeError]: {err}")
            print("  -> Дія системи: відхилення пакета конфігурації.")
        except KeyError as err:
            handled_faults += 1
            fault_stats["KeyError"] = fault_stats.get("KeyError", 0) + 1
            print(f"  [ПЕРЕХОПЛЕНО СТАНДАРТНИЙ KeyError]: {err}")
            print("  -> Дія системи: запит повної конфігурації від джерела.")
        except Exception as err:
            # Останній рубіж: непередбачена помилка, для якої не визначено дії відновлення
            unclassified_faults += 1
            print(f"  [НЕКЛАСИФІКОВАНИЙ ЗБІЙ]: {type(err).__name__}: {err}")
            print("  -> Дія системи: не визначена (потребує доопрацювання валідатора).")
        else:
            successful_runs += 1
            print(f"  [УСПІХ]: Конфігурація валідна. f_s = {result['sampling_rate_mhz']:.2f} МГц, "
                  f"період {result['sample_period_ns']:.2f} нс, "
                  f"смуга Найквіста {result['nyquist_mhz']:.2f} МГц.")
        finally:
            print(f"  [FINALLY]: Аудит тесту #{idx} завершено. Канали АЦП звільнено.")

    total_faults = handled_faults + unclassified_faults
    p_recovery = handled_faults / total_faults if total_faults > 0 else 1.0

    print("\n" + header_sep)
    print(f"{'ПІДСУМКОВІ МЕТРИКИ НАДІЙНОСТІ СИСТЕМИ':^90}")
    print(sub_sep)
    print(f"  Всього оброблено тестових наборів:         {total_configs:>5d}")
    print(f"  Штатних успішних конфігурацій:             {successful_runs:>5d}")
    print(f"  Усього нештатних ситуацій (N_total):       {total_faults:>5d}")
    print(f"  Локалізованих та оброблених (N_handled):   {handled_faults:>5d}")
    print(f"  Некласифікованих збоїв:                    {unclassified_faults:>5d}")
    for name, count in sorted(fault_stats.items()):
        print(f"      {name:<28} {count:>5d}")
    print(f"  Коефіцієнт програмного відновлення (P):   {p_recovery * 100:>7.2f}%")
    print(header_sep + "\n")


class FlakySensor:
    """
    Імітація апаратного датчика з несправною шиною: перетворення float() генерує
    TimeoutError, який валідатор не передбачає (не ValueError і не TypeError).
    """

    def __float__(self) -> float:
        raise TimeoutError("таймаут шини SPI під час зчитування датчика напруги")

    def __repr__(self) -> str:
        return "<FlakySensor: шина не відповідає>"


def main() -> None:
    """Головна точка входу лабораторної роботи."""
    test_suite = [
        # 1: коректна конфігурація
        {"sampling_rate_mhz": 50.0, "input_voltage_v": 1.2, "signal_freq_mhz": 10.0},
        # 2: коректна конфігурація на граничних значеннях (межі включено)
        {"sampling_rate_mhz": 100.0, "input_voltage_v": -2.5, "signal_freq_mhz": 20.0},
        # 3: частота вибірки вище максимуму
        {"sampling_rate_mhz": 125.0, "input_voltage_v": 1.0},
        # 4: частота вибірки нижче мінімуму
        {"sampling_rate_mhz": 0.5, "input_voltage_v": 1.0},
        # 5: перевантаження входу позитивною напругою
        {"sampling_rate_mhz": 80.0, "input_voltage_v": 3.1},
        # 6: перевантаження входу негативною напругою
        {"sampling_rate_mhz": 80.0, "input_voltage_v": -2.6},
        # 7: порушення критерію Найквіста (15 МГц >= 20 / 2)
        {"sampling_rate_mhz": 20.0, "input_voltage_v": 0.5, "signal_freq_mhz": 15.0},
        # 8: нечислове значення напруги (ланцюжок із ValueError)
        {"sampling_rate_mhz": 40.0, "input_voltage_v": "ERR_SENSOR"},
        # 9: відсутній обов'язковий ключ
        {"sampling_rate_mhz": 40.0},
        # 10: некоректний тип самої конфігурації
        None,
        # 11: непередбачений апаратний збій: датчик не відповідає (TimeoutError)
        {"sampling_rate_mhz": 40.0, "input_voltage_v": FlakySensor()},
    ]

    t_start = time.perf_counter()
    run_fault_tolerance_testbench(test_suite)
    t_elapsed = time.perf_counter() - t_start
    print(f"Час виконання діагностичного тестбенчу: {t_elapsed * 1000:.3f} мс\n")


if __name__ == "__main__":
    main()
