"""Тести парсера: два формати рядків, нормалізація, коментарі, помилки та ланцюжки винятків."""

import os
import tempfile
import unittest

from cpu_scheduler import (DuplicateProcessError, EmptyWorkloadError, InputFormatError,
                           InvalidBurstError, InvalidLineSyntaxError, WorkloadReadError,
                           load_workload, parse_workload_text)
from cpu_scheduler.parser import normalize_line, parse_line


class ParserTests(unittest.TestCase):
    def test_normalize_line(self):
        self.assertEqual(normalize_line("﻿  P1\t arrival=0   burst=5  # коментар"),
                         "P1 arrival=0 burst=5")
        self.assertEqual(normalize_line("   # лише коментар"), "")

    def test_key_value_and_csv_formats(self):
        w = parse_workload_text("P1 arrival=0 burst=5\nP2, 1, 3\np3;2;4\nP4 AT = 3 BT=6\n")
        self.assertEqual([(p.pid, p.arrival_time, p.burst_time) for p in w],
                         [("P1", 0, 5), ("P2", 1, 3), ("P3", 2, 4), ("P4", 3, 6)])

    def test_header_comments_and_blank_lines_skipped(self):
        w = parse_workload_text("# c\n\npid,arrival,burst\nP1,0,2\n")
        self.assertEqual(len(w), 1)

    def test_syntax_errors_report_line_number(self):
        bad_lines = ["P1 arrival=0", "P1 arrival=-1 burst=2", "1P arrival=0 burst=2",
                     "P1 arrival=0.5 burst=2", "P1 0 5", "just text"]
        for line in bad_lines:
            with self.assertRaises(InvalidLineSyntaxError) as ctx:
                parse_workload_text(f"P0 arrival=0 burst=1\n{line}\n")
            self.assertEqual(ctx.exception.line_no, 2)
            self.assertEqual(ctx.exception.error_code, 3001)

    def test_semantic_error_is_chained(self):
        with self.assertRaises(InputFormatError) as ctx:
            parse_line(7, "P1 arrival=0 burst=0")
        self.assertIsInstance(ctx.exception.__cause__, InvalidBurstError)
        self.assertIn("Рядок 7", str(ctx.exception))

    def test_duplicate_and_empty(self):
        with self.assertRaises(DuplicateProcessError):
            parse_workload_text("P1 arrival=0 burst=1\np1 arrival=3 burst=2\n")
        for text in ("", "   \n# нічого\n", "pid,arrival,burst\n"):
            with self.assertRaises(EmptyWorkloadError):
                parse_workload_text(text)

    def test_load_workload_file_and_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "w.txt")
            with open(path, "w", encoding="utf-8-sig") as handle:
                handle.write("P1 arrival=0 burst=5\n")
            self.assertEqual(len(load_workload(path)), 1)

    def test_load_workload_missing_file(self):
        with self.assertRaises(WorkloadReadError) as ctx:
            load_workload("/немає/такого/файлу.txt")
        self.assertIsInstance(ctx.exception.__cause__, OSError)

    def test_load_workload_bad_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "w.txt")
            with open(path, "wb") as handle:
                handle.write(b"P1 arrival=0 burst=5 \xff\xfe\n")
            with self.assertRaises(WorkloadReadError):
                load_workload(path)

    def test_directory_instead_of_file(self):
        with self.assertRaises(WorkloadReadError):
            load_workload(os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    unittest.main()
