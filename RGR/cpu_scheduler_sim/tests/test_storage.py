"""Тести збереження звітів: JSON-цикл, CSV, помилки запису/читання із ланцюжком причин."""

import csv
import json
import os
import tempfile
import unittest

from cpu_scheduler import (ReportReadError, ReportWriteError, RoundRobinScheduler, FIFOScheduler,
                           load_json, parse_workload_text, save_comparison_csv, save_csv, save_json)

WORKLOAD = "P1 arrival=0 burst=5\nP2 arrival=1 burst=3\nP3 arrival=9 burst=2\n"


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.result = RoundRobinScheduler(2, 1).schedule(parse_workload_text(WORKLOAD))

    def path(self, name):
        return os.path.join(self.tmp.name, name)

    def test_json_round_trip(self):
        target = save_json(self.result, self.path("sub/dir/report.json"))   # створює каталоги
        data = load_json(target)
        self.assertEqual(data, self.result.to_dict())
        self.assertEqual(data["parameters"], {"switch_cost": 1, "quantum": 2})
        self.assertEqual(len(data["processes"]), 3)

    def test_json_keeps_cyrillic_readable(self):
        save_json(self.result, self.path("r.json"))
        with open(self.path("r.json"), encoding="utf-8") as handle:
            self.assertIn('"algorithm": "RR"', handle.read())

    def test_csv_content(self):
        save_csv(self.result, self.path("r.csv"))
        with open(self.path("r.csv"), encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["pid"] for row in rows], ["P1", "P2", "P3"])
        for row, item in zip(rows, self.result):
            self.assertEqual(int(row["waiting"]), item.waiting)
            self.assertEqual(int(row["turnaround"]), item.turnaround)

    def test_comparison_csv(self):
        results = [FIFOScheduler().schedule(parse_workload_text(WORKLOAD)), self.result]
        save_comparison_csv(results, self.path("cmp.csv"))
        with open(self.path("cmp.csv"), encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["algorithm"] for row in rows], ["FIFO", "RR(q=2)"])

    def test_write_error_is_wrapped_and_chained(self):
        with self.assertRaises(ReportWriteError) as ctx:
            save_json(self.result, self.tmp.name)          # шлях - це каталог, а не файл
        self.assertIsInstance(ctx.exception.__cause__, OSError)
        self.assertEqual(ctx.exception.error_code, 6001)

    def test_read_errors(self):
        with self.assertRaises(ReportReadError):
            load_json(self.path("немає.json"))
        with open(self.path("bad.json"), "w", encoding="utf-8") as handle:
            handle.write("{не json")
        with self.assertRaises(ReportReadError) as ctx:
            load_json(self.path("bad.json"))
        self.assertIsInstance(ctx.exception.__cause__, json.JSONDecodeError)
        with open(self.path("alien.json"), "w", encoding="utf-8") as handle:
            json.dump({"hello": 1}, handle)
        with self.assertRaises(ReportReadError):
            load_json(self.path("alien.json"))


if __name__ == "__main__":
    unittest.main()
