"""
Головна точка входу консольної утиліти cpu_scheduler (РГР, тема № 2).
Приклади:
    python cli_main.py run --input data/workload_basic.txt --algo rr --quantum 4 --gantt
    python cli_main.py compare --input data/workload_basic.txt --quanta 1,2,4,8
Освітній компонент: Програмування на Python.
"""

import sys

from cpu_scheduler.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
