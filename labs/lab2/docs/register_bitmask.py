"""
Лабораторна робота № 2. Модуль 2 (Варіант 2).
Побітове упакування, розпакування та модифікація 16-бітного регістра передавача.
Поля: [15..12: UART_BAUD], [11: TX_BUSY], [10..2: FIFO_CNT], [1..0: MODE].
Операція варіанта: упакування полів та скидання прапорця TX_BUSY.
"""

import sys

# --- Бітові зсуви (Shift) та бітові маски (Mask) ---
# [15..12]: UART_BAUD — 4 біти (0b1111 = 0xF)
UART_BAUD_SHIFT = 12
UART_BAUD_MASK = 0xF

# [11]: TX_BUSY — 1 біт (0b1 = 0x1)
TX_BUSY_SHIFT = 11
TX_BUSY_MASK = 0x1

# [10..2]: FIFO_CNT — 9 бітів (0b1_1111_1111 = 0x1FF)
FIFO_CNT_SHIFT = 2
FIFO_CNT_MASK = 0x1FF

# [1..0]: MODE — 2 біти (0b11 = 0x3)
MODE_SHIFT = 0
MODE_MASK = 0x3


def pack_transmitter_register(uart_baud: int, tx_busy: bool, fifo_cnt: int, mode: int) -> int:
    """
    Упаковує параметри передавача у 16-бітний регістр за допомогою
    операцій зсуву (<<) та побітового логічного АБО (|).
    """
    # Валідація діапазонів значень бітових полів
    if not (0 <= uart_baud <= UART_BAUD_MASK):
        raise ValueError(f"UART_BAUD виходить за межі 4 бітів (0..15): {uart_baud}")
    if not (0 <= fifo_cnt <= FIFO_CNT_MASK):
        raise ValueError(f"FIFO_CNT виходить за межі 9 бітів (0..511): {fifo_cnt}")
    if not (0 <= mode <= MODE_MASK):
        raise ValueError(f"MODE виходить за межі 2 бітів (0..3): {mode}")

    busy_bit = 1 if tx_busy else 0

    # Побітове складання
    register_val = (
        (uart_baud << UART_BAUD_SHIFT)
        | (busy_bit << TX_BUSY_SHIFT)
        | (fifo_cnt << FIFO_CNT_SHIFT)
        | (mode << MODE_SHIFT)
    )
    return register_val & 0xFFFF


def unpack_transmitter_register(register_val: int) -> dict:
    """
    Розпаковує 16-бітне число у словник значень окремих бітових полів
    за допомогою бітових зсувів праворуч (>>) та масок І (&).
    """
    uart_baud = (register_val >> UART_BAUD_SHIFT) & UART_BAUD_MASK
    tx_busy = bool((register_val >> TX_BUSY_SHIFT) & TX_BUSY_MASK)
    fifo_cnt = (register_val >> FIFO_CNT_SHIFT) & FIFO_CNT_MASK
    mode = (register_val >> MODE_SHIFT) & MODE_MASK

    return {
        "uart_baud": uart_baud,
        "tx_busy": tx_busy,
        "fifo_cnt": fifo_cnt,
        "mode": mode,
    }


def clear_tx_busy(register_val: int) -> int:
    """
    Індивідуальне завдання Варіанта 2:
    Скидає прапорець TX_BUSY (біт 11) у 0 за допомогою операторів & та інверсії ~.
    """
    mask = ~(1 << TX_BUSY_SHIFT)
    # Маскуємо до 16 біт (0xFFFF), щоб коректно врахувати інверсію в Python
    return (register_val & mask) & 0xFFFF


def set_tx_busy(register_val: int) -> int:
    """Встановлює прапорець TX_BUSY (біт 11) у 1 за допомогою оператора |."""
    mask = 1 << TX_BUSY_SHIFT
    return (register_val | mask) & 0xFFFF


def toggle_tx_busy(register_val: int) -> int:
    """Інвертує стан прапорця TX_BUSY (біт 11) за допомогою XOR (^)."""
    mask = 1 << TX_BUSY_SHIFT
    return (register_val ^ mask) & 0xFFFF


def main() -> None:
    """Головна точка входу для тестування бітових операцій Варіанта 2."""
    print("=" * 80)
    print(f"{'ВАРІАНТ 2: УПАКУВАННЯ ТА МАНІПУЛЯЦІЯ РЕГІСТРОМ ПЕРЕДАВАЧА':^80}")
    print("=" * 80)

    # Початкові тестові параметри
    baud_rate = 9        # Швидкість (0..15, наприклад 9 -> 115200 бод)
    busy_flag = True     # Прапорець зайнятості TX_BUSY = 1
    fifo_counter = 345   # Кількість байт у черзі (0..511)
    work_mode = 2        # Режим роботи (0..3)

    # 1. Упакування полів у 16-бітний регістр
    reg_word = pack_transmitter_register(baud_rate, busy_flag, fifo_counter, work_mode)

    print(f"Вхідні дані:")
    print(f"  UART_BAUD = {baud_rate} (4 біти), TX_BUSY = {busy_flag} (біт 11),")
    print(f"  FIFO_CNT  = {fifo_counter} (9 бітів), MODE = {work_mode} (2 біти)")
    print("-" * 80)
    print(f"Упакований 16-бітний регістр:")
    print(f"  Десятковий формат (DEC): {reg_word}")
    print(f"  Шістнадцятковий (HEX):   0x{reg_word:04X}")
    print(f"  Двійковий формат (BIN):  0b{reg_word:016b}")
    print(f"  Вісімковий формат (OCT): 0o{reg_word:06o}")
    print("-" * 80)

    # 2. Розпакування та верифікація полів
    unpacked = unpack_transmitter_register(reg_word)
    print(f"{'ВЕРИФІКАЦІЯ РОЗПАКУВАННЯ':^80}")
    print(f"  UART_BAUD : {unpacked['uart_baud']} (очікувалося {baud_rate})")
    print(f"  TX_BUSY   : {unpacked['tx_busy']} (очікувалося {busy_flag})")
    print(f"  FIFO_CNT  : {unpacked['fifo_cnt']} (очікувалося {fifo_counter})")
    print(f"  MODE      : {unpacked['mode']} (очікувалося {work_mode})")
    print("-" * 80)

    # 3. Виконання основного завдання варіанта: Скидання прапорця TX_BUSY
    print(f"{'ВИКОНАННЯ ЗАВДАННЯ ВАРІАНТА: СКИДАННЯ TX_BUSY':^80}")
    reg_busy_cleared = clear_tx_busy(reg_word)
    unpacked_cleared = unpack_transmitter_register(reg_busy_cleared)

    print(f"  Стан до скидання:   0b{reg_word:016b} | TX_BUSY = {unpacked['tx_busy']}")
    print(f"  Після CLEAR_BUSY:   0b{reg_busy_cleared:016b} | TX_BUSY = {unpacked_cleared['tx_busy']}")
    print(f"  Нове значення HEX:  0x{reg_busy_cleared:04X}")
    print("-" * 80)

    # Додаткова перевірка встановлення та перемикання прапорця
    reg_busy_set = set_tx_busy(reg_busy_cleared)
    reg_busy_toggled = toggle_tx_busy(reg_busy_set)
    print(f"  Перевірка SET_BUSY:    0b{reg_busy_set:016b} | TX_BUSY = {unpack_transmitter_register(reg_busy_set)['tx_busy']}")
    print(f"  Перевірка TOGGLE_BUSY: 0b{reg_busy_toggled:016b} | TX_BUSY = {unpack_transmitter_register(reg_busy_toggled)['tx_busy']}")
    print("=" * 80)


if __name__ == "__main__":
    main()