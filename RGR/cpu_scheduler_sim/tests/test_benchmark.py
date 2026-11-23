"""Тести модуля benchmark: відтворюваність генератора та оцінка степеня складності."""

import unittest

from cpu_scheduler import FIFOScheduler, estimate_exponent, generate_workload, run_benchmark
from cpu_scheduler.benchmark import time_scheduler


class BenchmarkTests(unittest.TestCase):
    def test_generator_is_deterministic(self):
        self.assertEqual(generate_workload(50, seed=7), generate_workload(50, seed=7))
        self.assertNotEqual(generate_workload(50, seed=7), generate_workload(50, seed=8))
        w = generate_workload(30, seed=3)
        arrivals = [p.arrival_time for p in w]
        self.assertEqual(arrivals, sorted(arrivals))
        self.assertTrue(all(1 <= p.burst_time <= 20 for p in w))

    def test_estimate_exponent_on_exact_power_laws(self):
        sizes = [100, 200, 400, 800]
        self.assertAlmostEqual(estimate_exponent(sizes, [n * 1e-6 for n in sizes]), 1.0, places=6)
        self.assertAlmostEqual(estimate_exponent(sizes, [n * n * 1e-9 for n in sizes]), 2.0, places=6)

    def test_time_scheduler_and_rows(self):
        self.assertGreater(time_scheduler(FIFOScheduler(), generate_workload(20), repeats=2), 0)
        rows = run_benchmark([20, 40], quantum=4, repeats=1)
        self.assertEqual([(r["n"], r["algorithm"]) for r in rows],
                         [(20, "FIFO"), (20, "RR"), (40, "FIFO"), (40, "RR")])
        self.assertTrue(all(r["slices"] >= r["n"] for r in rows))


if __name__ == "__main__":
    unittest.main()
