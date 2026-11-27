"""Генератор демонстраційного журналу (детермінований, seed = 1).

Запуск: python tools/generate_sample_log.py [шлях]
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

NODES = {
    "TMP-001": (41.0, 3.0),
    "TMP-002": (47.0, 4.0),
    "VLT-001": (12.0, 0.12),
    "VLT-002": (11.95, 0.15),
    "FAN-001": (4200.0, 250.0),
    "FAN-002": (3900.0, 300.0),
}
START = datetime(2026, 3, 14, 10, 0, 0)

# Рядки, які програма має відхилити: (позиція, текст)
CORRUPTED = [
    (9, "TMP-001;0x00;41.5;2026-03-14T10:12:00"),
    (17, "garbage ### ??? ###"),
    (24, "VLT-002;0x0A00;12.01;2026-03-14T10:20:00"),
    (31, "TMP-002;0x0000;999.9;2026-03-14T10:25:00"),
    (38, "FAN-001;0x0000;4100;2026-13-40T10:30:00"),
    (46, "XYZ-001;0x0000;5.0;2026-03-14T10:35:00"),
    (52, "VLT-001;0x0000;abc;2026-03-14T10:40:00"),
    (60, "TMP-001;0xZZZZ;40.0;2026-03-14T10:45:00"),
]

# Показання з відмовами: індекс запису -> (регістр, значення)
FAULTS = {
    14: ("TMP-002", 0x0001, 93.4),     # перегрів
    21: ("VLT-001", 0x0002, 10.2),     # просідання напруги
    29: ("FAN-002", 0x0008, 0.0),      # вентилятор зупинено
    35: ("TMP-001", 0x0050, 44.0),     # LINK_DOWN + SENSOR_FAULT
    44: ("VLT-002", 0x0004, 13.9),     # перенапруга
    57: ("FAN-001", 0x0020, 4150.0),   # лише CRC_ERROR (попередження)
}


def build_lines(seed: int = 1, count: int = 66) -> list[str]:
    rng = random.Random(seed)
    names = list(NODES)
    lines = [
        "# Демонстраційний журнал телеметрії (згенеровано, seed=1)",
        "# вузол ; регістр стану ; значення ; часова мітка",
        "",
    ]
    for i in range(count):
        stamp = START + timedelta(minutes=i * 1, seconds=i % 7)
        if i in FAULTS:
            node, status, value = FAULTS[i]
        else:
            node = names[i % len(names)]
            mean, spread = NODES[node]
            value = rng.gauss(mean, spread)
            quality = rng.choice((0xF, 0xF, 0xE, 0xD))
            status = quality << 12
            if node.startswith("FAN"):
                value = round(value)
        if i in FAULTS:
            status |= 0xF000 & (rng.choice((0xF, 0xB)) << 12)
        text = (f"{node};0x{status:04X};{value:.2f};"
                f"{stamp:%Y-%m-%dT%H:%M:%S}")
        lines.append(text)
    for position, text in sorted(CORRUPTED):
        lines.insert(position + 3, text)
    return lines


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        __file__).resolve().parent.parent / "data" / "sample_telemetry.log"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(build_lines()) + "\n", encoding="utf-8")
    print(f"записано {target}")


if __name__ == "__main__":
    main()