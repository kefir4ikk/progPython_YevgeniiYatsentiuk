"""
Збір вимірюваних показників для пояснювальної записки: рядки коду, кількість тестів,
покриття, результати імітації відмов. Результат: results/metrics.json.
Запуск з кореня проєкту: python tools/collect_metrics.py
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from cpu_scheduler.cli import main  # noqa: E402

metrics = {}

# --- рядки коду ---
loc = {}
for folder in ("cpu_scheduler", "tests", "."):
    for name in sorted(os.listdir(folder)):
        if name.endswith(".py"):
            path = os.path.join(folder, name) if folder != "." else name
            if folder == "." and name != "cli_main.py":
                continue
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().splitlines()
            code = sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))
            loc[path.replace(os.sep, "/")] = {"total": len(lines), "code": code}
metrics["loc"] = loc

# --- тести ---
loader = unittest.TestLoader()
per_module = {}
for name in ("test_models", "test_parser", "test_schedulers", "test_storage", "test_cli", "test_benchmark"):
    suite = loader.loadTestsFromName(f"tests.{name}")
    per_module[name] = suite.countTestCases()
metrics["tests"] = per_module
metrics["tests_total"] = sum(per_module.values())

# --- покриття ---
subprocess.run([sys.executable, "-m", "coverage", "erase"], check=True)
subprocess.run([sys.executable, "-m", "coverage", "run", "--branch", "--source=cpu_scheduler",
                "-m", "unittest", "discover", "-s", "tests", "-t", "."],
               check=True, capture_output=True)
subprocess.run([sys.executable, "-m", "coverage", "json", "-o", "results/coverage.json", "-q"], check=True)
with open("results/coverage.json", encoding="utf-8") as handle:
    cov = json.load(handle)
metrics["coverage"] = {k.replace("\\", "/"): round(v["summary"]["percent_covered"], 1)
                       for k, v in cov["files"].items()}
metrics["coverage_total"] = round(cov["totals"]["percent_covered"], 1)
os.remove("results/coverage.json")
if os.path.exists(".coverage"):
    os.remove(".coverage")

# --- імітація відмов ---
tmp = tempfile.mkdtemp()


def write(name, text, mode="w", **kw):
    path = os.path.join(tmp, name)
    with open(path, mode, **kw) as handle:
        handle.write(text)
    return path


basic = "data/workload_basic.txt"
cases = [
    ("Вхідний файл відсутній", ["run", "--input", os.path.join(tmp, "no_such.txt")]),
    ("Вхідний шлях є каталогом", ["run", "--input", "data"]),
    ("Нечислова тривалість (burst=zero)", ["run", "--input", "data/bad_workload.txt"]),
    ("Від’ємний час надходження", ["run", "--input", write("neg.txt", "P1 arrival=-1 burst=2\n")]),
    ("Нульова тривалість процесу", ["run", "--input", write("zero.txt", "P1 arrival=0 burst=0\n")]),
    ("Повторний ідентифікатор процесу", ["run", "--input", write("dup.txt", "P1 arrival=0 burst=2\np1 arrival=1 burst=3\n")]),
    ("Порожній файл навантаження", ["run", "--input", write("empty.txt", "# лише коментар\n")]),
    ("Файл у неправильному кодуванні", ["run", "--input", write("bin.txt", b"P1 arrival=0 burst=5 \xff\xfe\n", "wb")]),
    ("Квант часу q = 0", ["run", "--input", basic, "--quantum", "0"]),
    ("Квант часу не є числом", ["run", "--input", basic, "--quantum", "abc"]),
    ("Від’ємна вартість перемикання", ["run", "--input", basic, "--switch-cost", "-1"]),
    ("Невідомий алгоритм", ["run", "--input", basic, "--algo", "sjf"]),
    ("Перевищено ліміт інтервалів", ["run", "--input", basic, "--quantum", "1", "--max-slices", "5"]),
    ("Звіт записується у каталог", ["run", "--input", basic, "--json", tmp]),
    ("Невідомий параметр командного рядка", ["run", "--input", basic, "--oops"]),
    ("Пропущено значення параметра", ["run", "--input"]),
    ("Невідома команда", ["bogus"]),
]
faults = []
for title, argv in cases:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(["cli_main.py", *argv])
    first = err.getvalue().splitlines()[0] if err.getvalue() else ""
    faults.append({"title": title, "args": " ".join(argv).replace(tmp, "<tmp>"), "exit_code": code,
                   "message": first.replace(tmp, "<tmp>")})
metrics["faults"] = faults

with open("results/metrics.json", "w", encoding="utf-8") as handle:
    json.dump(metrics, handle, ensure_ascii=False, indent=2)
print(json.dumps({k: metrics[k] for k in ("tests", "tests_total", "coverage_total")}, ensure_ascii=False))
for f in faults:
    print(f["exit_code"], f["title"], "|", f["message"][:100])
