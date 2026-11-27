"""Ручна мутаційна перевірка: кожна «поломка» коду має завалити тести.

Запуск: python tools/mutation_check.py
Код копіюється в тимчасовий каталог, оригінал не змінюється.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(__file__).resolve().parent.parent
PKG = "telemetry_monitor"
TIMEOUT = 60   # секунд на один мутант

# (файл, що замінити, на що замінити)
MUTANTS = [
    ("flags.py", "rest ^= lowest", "rest >>= 1"),
    ("flags.py", "rest &= rest - 1", "rest >>= 1"),
    ("flags.py", "(status >> QUALITY_SHIFT)", "(status >> 11)"),
    ("sensors.py", "if has_reserved_bits(new_status):", "if False:"),
    ("sensors.py", "not low <= new_value <= high",
     "not low < new_value < high"),
    ("sensors.py", "if temp > self.MAX_NOMINAL", "if temp >= 999"),
    ("sensors.py",
     "return hash((self.KIND, self._node_id, self._timestamp))",
     "return hash(self._value)"),
    ("parser.py", "0[xX][0-9A-Fa-f]{4}", "0[xX][0-9A-Fa-f]{2,4}"),
    ("parser.py", "if strict:\n                raise",
     "if False:\n                raise"),
    ("storage.py", 'encoding="utf-8-sig"', 'encoding="utf-8"'),
    ("storage.py", "os.replace(self._tmp_name, self._path)", "pass"),
    ("storage.py", "if exc_type is None:\n                os.replace",
     "if True:\n                os.replace"),
    ("analytics.py", "self.critical_count += sensor.is_critical",
     "self.critical_count += 0"),
    ("analytics.py", "self.flags_seen |= sensor.status",
     "self.flags_seen = sensor.status"),
    ("cli.py", "summary.rejected_ratio > max_error_ratio",
     "summary.rejected_ratio > 2"),
]


def main() -> None:
    killed = 0
    for name, old, new in MUTANTS:
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "p"
            shutil.copytree(SRC, copy, ignore=shutil.ignore_patterns(
                "__pycache__", ".coverage", "docs", "out", "tools"))
            target = copy / PKG / name
            text = target.read_text(encoding="utf-8")
            assert old in text, (name, old)
            target.write_text(text.replace(old, new, 1), encoding="utf-8")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "unittest", "discover", "-s",
                     "tests"], cwd=copy, capture_output=True, timeout=TIMEOUT)
                dead = result.returncode != 0
            except subprocess.TimeoutExpired:
                dead = True   # мутант зациклив програму: тести його виявили
        killed += dead
        label = "KILLED  " if dead else "SURVIVED"
        print(f"{label} {name}: {old.splitlines()[0][:48]}", flush=True)
    print(f"{killed}/{len(MUTANTS)}")


if __name__ == "__main__":
    main()