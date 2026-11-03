"""
Лабораторна робота № 5. Модуль 1. Варіант 2.
Базове очищення та нормалізація рядків системного журналу Linux Syslog
методами типу str та простим регулярним виразом.
Освітній компонент: Програмування на Python.
"""

import re

# Керуючі символи ASCII, окрім \t (0x09) та \n (0x0A): NUL, BEL, BS, VT, FF, ESC, DEL тощо
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def remove_control_chars(text: str) -> str:
    """Видаляє некоректні (керуючі) символи, що не несуть корисної інформації."""
    return _CONTROL_CHARS.sub("", text)


def collapse_whitespace(text: str) -> str:
    """
    Замінює будь-яку послідовність пробільних символів (пробіли, табуляції,
    нерозривні пробіли U+00A0) одним пробілом і прибирає крайні пробіли.
    split() без аргументів розбиває рядок за будь-яким пробільним символом
    і відкидає порожні лексеми, а join() збирає їх назад за O(N).
    """
    return " ".join(text.split())


def sanitize_log_line(raw_line: str) -> str:
    """Повний цикл очищення: керуючі символи -> нормалізація пробілів."""
    return collapse_whitespace(remove_control_chars(raw_line))


def main() -> None:
    """Невеликий самотест модуля на брудних рядках."""
    samples = [
        "  Sep  2\t08:15:02   srv-web01 nginx[2210]:   INFO: worker started \n",
        "Sep  2 08:18:00 srv-web01 cron[877]: INFO: (root)\u00a0CMD\u00a0(backup.sh)",
        "Sep  3 00:05:44 srv-web01 systemd[1]:\x07 ERR:\x00 service failed\r\n",
        "   \t  \n",
    ]
    print("=" * 78)
    print(f"{'ТЕСТ МОДУЛЯ ОЧИЩЕННЯ ТЕКСТУ':^78}")
    print("=" * 78)
    for idx, raw in enumerate(samples, start=1):
        clean = sanitize_log_line(raw)
        print(f"{idx}) до:    {raw!r}")
        print(f"   після: {clean!r}")
    print("=" * 78)


if __name__ == "__main__":
    main()
