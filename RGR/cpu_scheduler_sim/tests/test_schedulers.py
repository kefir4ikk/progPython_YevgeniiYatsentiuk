"""
Тести планувальників: еталонні приклади з літератури, аналітичні властивості, інваріанти
та перехресна перевірка з покроковим еталонним симулятором на випадкових наборах.
"""

import random
import unittest

from cpu_scheduler import (EmptyWorkloadError, FIFOScheduler, InvalidQuantumError,
                           InvalidSwitchCostError, Process, RoundRobinScheduler, SchedulerConfigError,
                           SimulationLimitExceededError, UnknownAlgorithmError, Workload,
                           create_scheduler, generate_workload, parse_workload_text)
from cpu_scheduler.models import KIND_IDLE, KIND_RUN, KIND_SWITCH
from tests.reference_sim import reference_simulate


def make(*triples):
    return Workload([Process(pid, a, b) for pid, a, b in triples])


class TextbookExamples(unittest.TestCase):
    """Приклад з Silberschatz et al.: P1=24, P2=3, P3=3, усі надходять у момент 0."""

    def setUp(self):
        self.w = make(("P1", 0, 24), ("P2", 0, 3), ("P3", 0, 3))

    def test_fifo_convoy_effect(self):
        r = FIFOScheduler().schedule(self.w)
        self.assertEqual([p.waiting for p in r], [0, 24, 27])
        self.assertAlmostEqual(r.avg_waiting, 17.0)
        self.assertEqual(r.end_time, 30)

    def test_fifo_reordered_has_smaller_waiting(self):
        r = FIFOScheduler().schedule(make(("P2", 0, 3), ("P3", 0, 3), ("P1", 0, 24)))
        self.assertAlmostEqual(r.avg_waiting, 3.0)

    def test_round_robin_q4(self):
        r = RoundRobinScheduler(4).schedule(self.w)
        self.assertEqual([p.waiting for p in r], [6, 4, 7])
        self.assertAlmostEqual(r.avg_waiting, 17 / 3)
        self.assertEqual([p.response for p in r], [0, 4, 7])
        self.assertEqual([(s.pid, s.start, s.end) for s in r.segments],
                         [("P1", 0, 4), ("P2", 4, 7), ("P3", 7, 10), ("P1", 10, 30)])
        self.assertEqual(r.context_switches, 3)


class ModelProperties(unittest.TestCase):
    def test_idle_gap_between_arrivals(self):
        r = FIFOScheduler().schedule(make(("P1", 2, 3), ("P2", 10, 2)))
        kinds = [(s.kind, s.start, s.end) for s in r.segments]
        self.assertEqual(kinds, [(KIND_RUN, 2, 5), (KIND_IDLE, 5, 10), (KIND_RUN, 10, 12)])
        self.assertEqual(r.start_time, 2)
        self.assertAlmostEqual(r.utilization, 100 * 5 / 10)

    def test_rr_arrival_at_quantum_end_enters_queue_before_preempted(self):
        # P1 (0,4) q=2; P2 надходить у момент 2 - рівно в кінці першого кванта
        r = RoundRobinScheduler(2).schedule(make(("P1", 0, 4), ("P2", 2, 2)))
        self.assertEqual([(s.pid, s.start, s.end) for s in r.segments],
                         [("P1", 0, 2), ("P2", 2, 4), ("P1", 4, 6)])

    def test_single_process_rr_segments_are_merged(self):
        r = RoundRobinScheduler(2).schedule(make(("P1", 0, 7)))
        self.assertEqual(len(r.segments), 1)
        self.assertEqual(r.slices, 4)
        self.assertEqual(r.context_switches, 0)

    def test_switch_cost_is_charged_between_different_processes(self):
        r = RoundRobinScheduler(2, switch_cost=1).schedule(make(("P1", 0, 3), ("P2", 0, 3)))
        self.assertEqual([(s.kind, s.start, s.end) for s in r.segments],
                         [(KIND_RUN, 0, 2), (KIND_SWITCH, 2, 3), (KIND_RUN, 3, 5),
                          (KIND_SWITCH, 5, 6), (KIND_RUN, 6, 7), (KIND_SWITCH, 7, 8),
                          (KIND_RUN, 8, 9)])
        self.assertEqual(r.context_switches, 3)
        self.assertEqual(r.switch_time, 3)

    def test_quantum_larger_than_every_burst_equals_fifo(self):
        for seed in range(30):
            w = generate_workload(25, seed=seed)
            fifo = FIFOScheduler(1).schedule(w)
            rr = RoundRobinScheduler(10 ** 6, 1).schedule(w)
            self.assertEqual([p.completion for p in fifo], [p.completion for p in rr])

    def test_rr_response_bound_for_simultaneous_arrival(self):
        # Для n процесів, що надійшли в момент 0, без накладних витрат: R_i <= (n - 1) * q
        for seed in range(30):
            rng = random.Random(seed)
            n, q = rng.randint(2, 12), rng.randint(1, 6)
            w = make(*[(f"P{i}", 0, rng.randint(1, 30)) for i in range(n)])
            r = RoundRobinScheduler(q).schedule(w)
            self.assertTrue(all(p.response <= (n - 1) * q for p in r))

    def test_invariants_on_random_workloads(self):
        for seed in range(60):
            rng = random.Random(seed)
            w = generate_workload(rng.randint(1, 40), seed=seed, max_gap=rng.randint(0, 12))
            sched = rng.choice([FIFOScheduler(rng.randint(0, 3)),
                                RoundRobinScheduler(rng.randint(1, 9), rng.randint(0, 3))])
            r = sched.schedule(w)
            # час інтервалів розбивається на виконання, простій і перемикання
            self.assertEqual(r.busy_time + r.idle_time + r.switch_time, r.makespan)
            self.assertEqual(r.busy_time, w.total_burst)
            for p in r:
                self.assertGreaterEqual(p.completion, p.arrival + p.burst)
                self.assertGreaterEqual(p.waiting, 0)
                self.assertGreaterEqual(p.first_start, p.arrival)
            # кожен процес отримує рівно b_i одиниць процесорного часу
            run = {}
            for s in r.segments:
                if s.kind == KIND_RUN:
                    run[s.pid] = run.get(s.pid, 0) + s.duration
            self.assertEqual(run, {p.pid: p.burst_time for p in w})
            # інтервали не перекриваються і йдуть підряд
            segs = r.segments
            self.assertTrue(all(a.end == b.start for a, b in zip(segs, segs[1:])))


class CrossValidation(unittest.TestCase):
    """Подієвий планувальник пакета проти покрокового еталона на 400 випадкових наборах."""

    def test_matches_reference_simulator(self):
        for seed in range(400):
            rng = random.Random(seed)
            n = rng.randint(1, 14)
            triples = [(f"P{i}", rng.randint(0, 25), rng.randint(1, 12)) for i in range(n)]
            quantum = rng.choice([None, 1, 2, 3, 5, 8])
            sigma = rng.choice([0, 0, 1, 2])
            w = make(*triples)
            sched = FIFOScheduler(sigma) if quantum is None else RoundRobinScheduler(quantum, sigma)
            r = sched.schedule(w)
            completion, first_start, switches, ticks = reference_simulate(triples, quantum, sigma)
            ctx = f"seed={seed} q={quantum} sigma={sigma} {triples}"
            self.assertEqual({p.pid: p.completion for p in r}, completion, ctx)
            self.assertEqual({p.pid: p.first_start for p in r}, first_start, ctx)
            self.assertEqual(r.context_switches, switches, ctx)
            # розгортання інтервалів у позначки по одиницях часу збігається з еталоном
            flat = []
            for s in r.segments:
                label = s.pid if s.kind == KIND_RUN else s.kind
                flat += [label] * s.duration
            self.assertEqual(flat, ticks, ctx)


class ConfigAndFactory(unittest.TestCase):
    def test_quantum_validation(self):
        for bad in (0, -1, 2.5, "4", True, None):
            with self.assertRaises(InvalidQuantumError):
                RoundRobinScheduler(bad)

    def test_switch_cost_validation(self):
        for bad in (-1, 1.5, "1", True):
            with self.assertRaises(InvalidSwitchCostError):
                FIFOScheduler(bad)

    def test_quantum_property_setter(self):
        rr = RoundRobinScheduler(3)
        rr.quantum = 5
        self.assertEqual(rr.quantum, 5)
        with self.assertRaises(InvalidQuantumError):
            rr.quantum = 0
        self.assertEqual(rr.quantum, 5)

    def test_factory(self):
        self.assertIsInstance(create_scheduler("FIFO"), FIFOScheduler)
        self.assertEqual(create_scheduler(" rr ", quantum=3).quantum, 3)
        with self.assertRaises(UnknownAlgorithmError):
            create_scheduler("sjf")
        with self.assertRaises(InvalidQuantumError):
            create_scheduler("rr")
        self.assertTrue(issubclass(UnknownAlgorithmError, SchedulerConfigError))

    def test_empty_workload(self):
        with self.assertRaises(EmptyWorkloadError):
            FIFOScheduler().schedule(Workload())

    def test_slice_limit(self):
        w = make(("P1", 0, 1000))
        with self.assertRaises(SimulationLimitExceededError) as ctx:
            RoundRobinScheduler(1, max_slices=100).schedule(w)
        self.assertEqual(ctx.exception.limit, 100)

    def test_slice_limit_boundary(self):
        w = make(("P1", 0, 10))                          # q=1 -> рівно 10 інтервалів
        self.assertEqual(RoundRobinScheduler(1, max_slices=10).schedule(w).slices, 10)
        with self.assertRaises(SimulationLimitExceededError):
            RoundRobinScheduler(1, max_slices=9).schedule(w)

    def test_result_comparison_and_dunders(self):
        w = parse_workload_text("P1 arrival=0 burst=24\nP2 arrival=0 burst=3\nP3 arrival=0 burst=3")
        fifo, rr = FIFOScheduler().schedule(w), RoundRobinScheduler(4).schedule(w)
        self.assertLess(rr, fifo)                       # __lt__: RR кращий за середнім очікуванням
        self.assertIs(min([fifo, rr]), rr)
        self.assertEqual(len(rr), 3)
        self.assertEqual(rr["p2"].waiting, 4)
        self.assertEqual(rr[0].pid, "P1")
        self.assertEqual(rr.label, "RR(q=4)")
        self.assertIn("RR(q=4)", repr(rr))


if __name__ == "__main__":
    unittest.main()
