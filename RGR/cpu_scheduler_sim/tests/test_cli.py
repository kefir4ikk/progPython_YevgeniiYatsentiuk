"""Тести консольного інтерфейсу: команди, розбір sys.argv, коди завершення, ізольовані файли."""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest

from cpu_scheduler.cli import exit_code_for, main, parse_options
from cpu_scheduler import CliUsageError, InvalidQuantumError, SimulationLimitExceededError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASIC = os.path.join(ROOT, "data", "workload_basic.txt")


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(["cli_main.py", *args])
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def test_help_and_version(self):
        for argv in ([], ["--help"], ["-h"]):
            code, out, _ = run_cli(*argv)
            self.assertEqual(code, 0)
            self.assertIn("ВИКОРИСТАННЯ", out)
        self.assertEqual(run_cli("--version")[0], 0)

    def test_run_rr_prints_expected_metrics(self):
        code, out, _ = run_cli("run", "--input", BASIC, "--algo", "rr", "--quantum", "4", "--gantt")
        self.assertEqual(code, 0)
        self.assertIn("5.667", out)
        self.assertIn("Діаграма Ганта", out)

    def test_run_fifo(self):
        code, out, _ = run_cli("run", "--input", BASIC, "--algo", "fifo")
        self.assertEqual(code, 0)
        self.assertIn("17.000", out)

    def test_compare_marks_best(self):
        code, out, _ = run_cli("compare", "--input", BASIC, "--quanta", "1,4")
        self.assertEqual(code, 0)
        self.assertIn("RR(q=4)", out)
        self.assertIn("*", out)

    def test_outputs_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            j, c = os.path.join(tmp, "o", "r.json"), os.path.join(tmp, "o", "r.csv")
            code, out, _ = run_cli("run", "--input", BASIC, "--quantum", "3", "--json", j, "--csv", c)
            self.assertEqual(code, 0)
            self.assertTrue(os.path.getsize(j) > 0 and os.path.getsize(c) > 0)

    def test_generate_then_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "g.txt")
            self.assertEqual(run_cli("generate", "--count", "15", "--output", target)[0], 0)
            self.assertEqual(run_cli("run", "--input", target, "--quantum", "5")[0], 0)

    def test_benchmark_small(self):
        code, out, _ = run_cli("benchmark", "--sizes", "50,100", "--repeats", "1")
        self.assertEqual(code, 0)
        self.assertIn("Емпіричний показник", out)

    def test_exit_codes(self):
        cases = [
            (("bogus",), 1),                                   # невідома команда
            (("run",), 1),                                     # немає --input
            (("run", "--input"), 1),                           # немає значення
            (("run", "--input", BASIC, "--oops"), 1),          # невідомий прапорець
            (("run", "--input", "/немає.txt"), 2),             # файл відсутній
            (("run", "--input", BASIC, "--quantum", "0"), 3),  # квант 0
            (("run", "--input", BASIC, "--quantum", "abc"), 3),
            (("run", "--input", BASIC, "--algo", "sjf"), 3),
            (("run", "--input", BASIC, "--quantum", "1", "--max-slices", "5"), 4),
        ]
        for args, expected in cases:
            code, _, err = run_cli(*args)
            self.assertEqual(code, expected, f"{args}: {err}")
            self.assertIn("Помилка", err)

    def test_bad_input_file_code_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.txt")
            with open(bad, "w", encoding="utf-8") as handle:
                handle.write("P1 arrival=0 burst=oops\n")
            code, _, err = run_cli("run", "--input", bad)
            self.assertEqual(code, 2)
            self.assertIn("Рядок 1", err)

    def test_unwritable_report_code_5(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, _ = run_cli("run", "--input", BASIC, "--json", tmp)   # каталог замість файлу
            self.assertEqual(code, 5)

    def test_parse_options_and_exit_code_mapping(self):
        self.assertEqual(parse_options(["--a", "1", "--f"], {"--a": True, "--f": False}),
                         {"--a": "1", "--f": True})
        with self.assertRaises(CliUsageError):
            parse_options(["--a", "--f"], {"--a": True, "--f": False})
        self.assertEqual(exit_code_for(InvalidQuantumError("x")), 3)
        self.assertEqual(exit_code_for(SimulationLimitExceededError(1)), 4)
        self.assertEqual(exit_code_for(RuntimeError()), 70)

    def test_entry_point_as_subprocess(self):
        proc = subprocess.run([sys.executable, os.path.join(ROOT, "cli_main.py"), "run",
                               "--input", BASIC, "--quantum", "4"],
                              capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertEqual(proc.returncode, 0)
        proc = subprocess.run([sys.executable, "-m", "cpu_scheduler", "--version"],
                              capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1.0.0", proc.stdout)


if __name__ == "__main__":
    unittest.main()
