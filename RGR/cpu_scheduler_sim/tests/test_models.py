"""Тести предметних класів: валідація, інкапсуляція, dunder-методи, формули показників."""

import unittest

from cpu_scheduler import (DuplicateProcessError, InvalidArrivalError, InvalidBurstError, Process,
                           ProcessParameterError, ProcessResult, Workload)


class ProcessTests(unittest.TestCase):
    def test_normalization_and_properties(self):
        p = Process(" p1 ", 3, 5)
        self.assertEqual((p.pid, p.arrival_time, p.burst_time), ("P1", 3, 5))

    def test_pid_is_read_only(self):
        p = Process("P1", 0, 1)
        with self.assertRaises(AttributeError):
            p.pid = "P2"

    def test_private_attributes_are_mangled(self):
        p = Process("P1", 0, 1)
        self.assertFalse(hasattr(p, "__burst_time"))
        self.assertTrue(hasattr(p, "_Process__burst_time"))

    def test_invalid_values(self):
        for bad in (-1, 1.5, "3", True, None):
            with self.assertRaises(InvalidArrivalError):
                Process("P1", bad, 1)
        for bad in (0, -4, 2.0, "x", False):
            with self.assertRaises(InvalidBurstError):
                Process("P1", 0, bad)
        for bad in ("", "1P", "P 1", "P" * 17, "Ж1"):
            with self.assertRaises(ProcessParameterError):
                Process(bad, 0, 1)

    def test_setters_validate(self):
        p = Process("P1", 0, 1)
        p.burst_time = 7
        self.assertEqual(p.burst_time, 7)
        with self.assertRaises(InvalidBurstError):
            p.burst_time = 0
        self.assertEqual(p.burst_time, 7)           # стан не змінився після відхилення

    def test_equality_ordering_repr(self):
        a, b = Process("P1", 0, 5), Process("P2", 1, 5)
        self.assertEqual(a, Process("p1", 0, 5))
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, "P1")
        self.assertLess(a, b)
        self.assertEqual(sorted([b, a]), [a, b])
        self.assertEqual(eval(repr(a)), a)           # repr відтворює об'єкт
        with self.assertRaises(TypeError):
            hash(a)                                  # змінюваний об'єкт не хешується


class WorkloadTests(unittest.TestCase):
    def setUp(self):
        self.w = Workload([Process("P1", 0, 5), Process("P2", 2, 3)])

    def test_sequence_protocol(self):
        self.assertEqual(len(self.w), 2)
        self.assertEqual(self.w[0].pid, "P1")
        self.assertEqual(self.w["p2"].burst_time, 3)
        self.assertEqual([p.pid for p in self.w[0:2]], ["P1", "P2"])
        self.assertIn("P1", self.w)
        self.assertNotIn("P9", self.w)
        self.assertEqual([p.pid for p in self.w], ["P1", "P2"])
        with self.assertRaises(KeyError):
            self.w["P9"]

    def test_duplicate_rejected(self):
        with self.assertRaises(DuplicateProcessError):
            self.w.add(Process("P1", 9, 9))

    def test_add_operator_creates_new_workload(self):
        other = Workload([Process("P3", 4, 1)])
        merged = self.w + other
        self.assertEqual(len(merged), 3)
        self.assertEqual(len(self.w), 2)             # операнди не змінюються
        self.assertIs(self.w.__add__(5), NotImplemented)
        with self.assertRaises(DuplicateProcessError):
            self.w + self.w

    def test_aggregates(self):
        self.assertEqual(self.w.total_burst, 8)
        self.assertEqual(self.w.earliest_arrival, 2 - 2)
        self.assertEqual(Workload().earliest_arrival, 0)


class ProcessResultTests(unittest.TestCase):
    def test_formulas(self):
        r = ProcessResult("P1", arrival=2, burst=4, first_start=5, completion=13)
        self.assertEqual(r.turnaround, 11)           # C - a
        self.assertEqual(r.waiting, 7)               # T - b
        self.assertEqual(r.response, 3)              # s - a
        self.assertAlmostEqual(r.slowdown, 11 / 4)


if __name__ == "__main__":
    unittest.main()
