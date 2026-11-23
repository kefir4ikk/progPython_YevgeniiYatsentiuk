"""
Ручна мутаційна перевірка тестів: у копії schedulers.py вносяться поодинокі «мутації»,
після кожної запускається набір тестів; мутант вважається «убитим», якщо тести падають.
Результат: results/mutation.json. Запуск з кореня проєкту: python tools/mutation_check.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MUTANTS = [
    ("M1", "FIFO: ігнорування простою (>= замість >)",
     "if process.arrival_time > timeline.clock:", "if process.arrival_time >= timeline.clock:"),
    ("M2", "RR: допуск нових процесів лише строго до кінця кванта (<= -> <)",
     "pending[admitted].arrival_time <= timeline.clock", "pending[admitted].arrival_time < timeline.clock"),
    ("M3", "RR: квант не обмежується залишком (min прибрано)",
     "piece = min(self.quantum, remaining[pid])", "piece = self.quantum"),
    ("M4", "RR: витіснений процес стає в чергу раніше за нових",
     "            admit_arrived()                # нові процеси - раніше за витіснений (угода 4)\n"
     "            if remaining[pid] == 0:",
     "            if remaining[pid] == 0:"),
    ("M5", "Перемикання контексту не оплачується (sigma ігнорується)",
     "self.clock += self._switch_cost", "self.clock += 0"),
    ("M6", "Перемикання після простою теж рахується (last_pid не скидається)",
     "        self._last_pid = None\n\n    def run", "        pass\n\n    def run"),
    ("M7", "Лічильник перемикань не збільшується",
     "self.context_switches += 1", "self.context_switches += 0"),
    ("M8", "Ліміт інтервалів порівнюється нестрого (> -> >=)",
     "if self.slices > self._max_slices:", "if self.slices >= self._max_slices:"),
    ("M9", "Нестабільне впорядкування у FIFO (reverse=True)",
     "for process in sorted(workload, key=lambda p: p.arrival_time):",
     "for process in sorted(workload, key=lambda p: p.arrival_time, reverse=True):"),
    ("M10", "Квант допускає 0 (мінімум 1 -> 0)",
     '"Квант часу", 1)', '"Квант часу", 0)'),
]

results = []
tmp = tempfile.mkdtemp()
work = os.path.join(tmp, "proj")
shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns("__pycache__", "docs", "results"))
target = os.path.join(work, "cpu_scheduler", "schedulers.py")
with open(target, encoding="utf-8") as handle:
    original = handle.read()

for mid, title, old, new in MUTANTS:
    if old not in original:
        results.append({"id": mid, "title": title, "status": "НЕ ЗАСТОСОВАНО"})
        continue
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(original.replace(old, new, 1))
    try:
        run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                             cwd=work, capture_output=True, text=True, timeout=40)
        status = "убито" if run.returncode != 0 else "вижив"
    except subprocess.TimeoutExpired:      # мутант зациклив симулятор - тест не завершився
        status = "убито"
    results.append({"id": mid, "title": title, "status": status})
with open(target, "w", encoding="utf-8") as handle:
    handle.write(original)

killed = sum(1 for r in results if r["status"] == "убито")
payload = {"mutants": results, "killed": killed, "total": len(results)}
os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
with open(os.path.join(ROOT, "results", "mutation.json"), "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2)
shutil.rmtree(tmp, ignore_errors=True)
for r in results:
    print(r["id"], r["status"], "-", r["title"])
print(f"Убито {killed} з {len(results)}")
