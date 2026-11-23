"""
Експеримент: вплив кванта часу q на показники Round Robin при вартості перемикання sigma = 1.
Результат: results/quantum_study.csv. Запуск: python tools/quantum_study.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cpu_scheduler import FIFOScheduler, RoundRobinScheduler, generate_workload  # noqa: E402

SIGMA = 1
workload = generate_workload(40, seed=7, max_gap=3, max_burst=20)
rows = []
fifo = FIFOScheduler(SIGMA).schedule(workload)
rows.append({"algorithm": "FIFO", "quantum": "", **fifo.summary()})
for q in list(range(1, 31)) + [40]:
    res = RoundRobinScheduler(q, SIGMA).schedule(workload)
    rows.append({"algorithm": "RR", "quantum": q, **{k: v for k, v in res.summary().items() if k != "algorithm"}})

os.makedirs("results", exist_ok=True)
with open("results/quantum_study.csv", "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[1].keys()))
    writer.writeheader()
    writer.writerows(rows)

best = min((r for r in rows if r["algorithm"] == "RR"), key=lambda r: r["avg_waiting"])
print(f"FIFO: W={fifo.avg_waiting:.2f} R={fifo.avg_response:.2f} U={fifo.utilization:.1f}%")
print(f"RR найкращий за W: q={best['quantum']} W={best['avg_waiting']} R={best['avg_response']} U={best['utilization_percent']}")
print("q=1:", rows[1]["avg_waiting"], rows[1]["avg_response"], rows[1]["utilization_percent"], rows[1]["context_switches"])
