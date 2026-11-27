"""Тести ядра: прапорці, сенсори, шаблон, розбір, аналітика."""

import math
import unittest
from collections import Counter
from datetime import datetime

from telemetry_monitor import exceptions as exc
from telemetry_monitor.analytics import aggregate, filter_records
from telemetry_monitor.flags import (
    CRITICAL_MASK,
    StatusFlags,
    critical_part,
    decode_flags,
    has_reserved_bits,
    popcount,
    quality_of,
    set_bit_positions,
)
from telemetry_monitor.parser import (
    RECORD_PATTERN,
    ParseStats,
    parse_line,
    parse_stream,
    split_record,
)
from telemetry_monitor.sensors import (
    BaseSensor,
    FanSensor,
    TemperatureSensor,
    VoltageSensor,
    create_sensor,
    known_kinds,
)

T0 = datetime(2026, 3, 14, 10, 0, 0)


def line(node="TMP-001", status="0x0000", value="40.0",
         stamp="2026-03-14T10:00:00"):
    return f"{node};{status};{value};{stamp}"


class FlagsTest(unittest.TestCase):
    def test_set_bit_positions(self):
        self.assertEqual(set_bit_positions(0b1010_0101), (0, 2, 5, 7))
        self.assertEqual(set_bit_positions(0), ())

    def test_positions_ignore_quality_nibble(self):
        self.assertEqual(set_bit_positions(0xF001), (0,))

    def test_popcount_matches_builtin(self):
        for status in range(0, 0x100):
            self.assertEqual(popcount(status), bin(status).count("1"))

    def test_decode_flags_names(self):
        flags = decode_flags(0x0009)
        self.assertEqual(flags, (StatusFlags.OVER_TEMP,
                                 StatusFlags.FAN_FAILURE))

    def test_quality_and_reserved(self):
        self.assertEqual(quality_of(0xB001), 0xB)
        self.assertTrue(has_reserved_bits(0x0100))
        self.assertFalse(has_reserved_bits(0xF0FF))

    def test_critical_part(self):
        self.assertEqual(critical_part(0x00FF), CRITICAL_MASK)
        self.assertEqual(critical_part(0x00B0), 0)   # лише попередження


class SensorTest(unittest.TestCase):
    def make(self, cls=TemperatureSensor, node="TMP-001", status=0,
             value=40.0):
        return cls(node, status, value, T0)

    def test_abstract_base_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            BaseSensor("TMP-001", 0, 1.0, T0)

    def test_registry(self):
        self.assertEqual(known_kinds(), ("FAN", "TMP", "VLT"))
        self.assertIsInstance(
            create_sensor("VLT-002", 0, 12.0, T0), VoltageSensor)

    def test_unknown_kind(self):
        with self.assertRaises(exc.UnknownSensorKindError):
            create_sensor("ABC-001", 0, 1.0, T0)

    def test_node_must_match_kind(self):
        with self.assertRaises(ValueError):
            TemperatureSensor("VLT-001", 0, 1.0, T0)

    def test_value_setter_validates(self):
        sensor = self.make()
        sensor.value = 55.5
        self.assertEqual(sensor.value, 55.5)
        for bad in (200.0, -60.0, math.nan, math.inf):
            with self.assertRaises(exc.ValueOutOfRangeError):
                sensor.value = bad
        self.assertEqual(sensor.value, 55.5)   # стан не зіпсовано

    def test_status_setter_validates(self):
        sensor = self.make()
        for bad in (0x1_0000, -1, 0x0100, "0x1", 1.5, True):
            with self.assertRaises(exc.InvalidStatusError, msg=repr(bad)):
                sensor.status = bad

    def test_node_id_is_read_only(self):
        with self.assertRaises(AttributeError):
            self.make().node_id = "TMP-009"

    def test_no_instance_dict(self):
        self.assertFalse(hasattr(self.make(), "__dict__"))

    def test_str_repr_eq_hash(self):
        a, b = self.make(), self.make()
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(len({a, b}), 1)
        self.assertNotEqual(a, self.make(value=41.0))
        self.assertNotEqual(a, self.make(cls=FanSensor, node="FAN-001"))
        self.assertIn("TMP-001", str(a))
        self.assertTrue(repr(a).startswith("TemperatureSensor("))
        self.assertEqual(a.__eq__(object()), NotImplemented)

    def test_hash_survives_mutation_of_value(self):
        sensor = self.make()
        bucket = {sensor}
        sensor.value = 60.0   # значення змінне, хеш від нього не залежить
        self.assertIn(sensor, bucket)

    def test_critical_by_flag_and_by_value(self):
        self.assertFalse(self.make().is_critical)
        self.assertTrue(self.make(status=0x0001).is_critical)
        self.assertTrue(self.make(value=90.0).is_critical)
        self.assertFalse(self.make(status=0x0010).is_critical)  # LINK_DOWN

    def test_calibration_applies_to_threshold(self):
        # 85.2 − 0.5 = 84.7 → ще в нормі
        self.assertFalse(self.make(value=85.2).is_critical)
        self.assertTrue(self.make(value=85.6).is_critical)

    def test_diagnose_lists_all_reasons(self):
        reasons = self.make(status=0x0001, value=95.0).diagnose()
        self.assertEqual(len(reasons), 2)
        self.assertIn("OVER_TEMP", reasons[0])

    def test_warning_vs_critical_flags(self):
        sensor = self.make(status=0x0051)
        self.assertEqual(sensor.critical_flags,
                         (StatusFlags.OVER_TEMP, StatusFlags.SENSOR_FAULT))
        self.assertEqual(sensor.warning_flags, (StatusFlags.LINK_DOWN,))

    def test_fan_and_voltage_nominal(self):
        self.assertTrue(FanSensor("FAN-001", 0, 500.0, T0).is_critical)
        self.assertFalse(FanSensor("FAN-001", 0, 3000.0, T0).is_critical)
        self.assertTrue(VoltageSensor("VLT-001", 0, 13.5, T0).is_critical)
        self.assertFalse(VoltageSensor("VLT-001", 0, 12.0, T0).is_critical)

    def test_mro_is_c3(self):
        names = [c.__name__ for c in TemperatureSensor.__mro__]
        self.assertEqual(names, [
            "TemperatureSensor", "ThermalSensor", "BaseSensor",
            "SerializableMixin", "ABC", "CalibratedMixin", "object"])

    def test_as_dict(self):
        data = self.make().as_dict()
        self.assertEqual(data["unit"], "°C")
        self.assertEqual(data["kind"], "TMP")


class PatternTest(unittest.TestCase):
    def test_accepts_valid(self):
        for text in (line(), line(value="-5"), line(value="+1.5e2"),
                     line(node="FAN-1234", status="0xabcd"),
                     " TMP-001 ; 0X00Ff ; 3.0 ; 2026-03-14T10:00:00 "):
            self.assertIsNotNone(RECORD_PATTERN.match(text), text)

    def test_rejects_invalid(self):
        for text in (line(status="0x00"), line(status="0x00000"),
                     line(status="00A5"), line(node="tmp-001"),
                     line(node="TMP-01"), line(value="abc"),
                     line(value="1,5"), line(stamp="2026-03-14 10:00:00"),
                     line() + ";extra", "", "TMP-001"):
            self.assertIsNone(RECORD_PATTERN.match(text), text)

    def test_named_groups(self):
        m = RECORD_PATTERN.match(line(node="VLT-002", status="0x00A5"))
        self.assertEqual(m["kind"], "VLT")
        self.assertEqual(m["num"], "002")
        self.assertEqual(int(m["status"], 16), 0xA5)

    def test_split_record_returns_tuple(self):
        raw = split_record(line(value="12.5", status="0xB002"))
        self.assertIsInstance(raw, tuple)
        self.assertEqual(raw.status, 0xB002)
        self.assertEqual(raw.value, 12.5)
        self.assertEqual(raw.timestamp, T0)

    def test_no_catastrophic_backtracking(self):
        import time
        evil = "TMP-001;0x0000;" + "1" * 50_000 + "x"
        started = time.perf_counter()
        self.assertIsNone(RECORD_PATTERN.match(evil))
        self.assertLess(time.perf_counter() - started, 0.5)


class ParserTest(unittest.TestCase):
    def test_error_types(self):
        cases = {
            "": exc.MalformedRecordError,
            line(stamp="2026-02-30T10:00:00"): exc.InvalidTimestampError,
            line(node="QQQ-001"): exc.UnknownSensorKindError,
            line(status="0x0F00"): exc.InvalidStatusError,
            line(value="500"): exc.ValueOutOfRangeError,
            line(value="1e999"): exc.ValueOutOfRangeError,
        }
        for text, error in cases.items():
            with self.assertRaises(error, msg=text):
                parse_line(text, 7)

    def test_error_carries_line_number(self):
        with self.assertRaises(exc.RecordError) as ctx:
            parse_line("мусор", 12)
        self.assertEqual(ctx.exception.line_no, 12)
        self.assertEqual(ctx.exception.raw, "мусор")
        self.assertIn("рядок 12", str(ctx.exception))

    def test_hierarchy(self):
        self.assertTrue(issubclass(exc.InvalidStatusError, exc.RecordError))
        self.assertTrue(issubclass(exc.LogAccessError, exc.StorageError))
        self.assertTrue(issubclass(exc.StorageError, exc.TelemetryError))
        self.assertFalse(issubclass(exc.StorageError, exc.RecordError))
        codes = [getattr(exc, n).code for n in exc.__all__]
        self.assertEqual(len(codes), len(set(codes)))

    def test_stream_is_lazy_generator(self):
        consumed = []

        def source():
            for text in (line(), line(node="VLT-001", value="12"), line()):
                consumed.append(text)
                yield text

        stream = parse_stream(source())
        next(stream)
        self.assertEqual(len(consumed), 1)

    def test_stream_collects_rejected_and_skips_comments(self):
        stats = ParseStats()
        rows = ["# коментар", "", line(), "мусор", line(value="500"),
                line()]
        good = list(parse_stream(rows, stats=stats))
        self.assertEqual(len(good), 2)
        self.assertEqual(stats.skipped, 2)
        self.assertEqual(stats.lines, 6)
        self.assertEqual(len(stats.rejected), 2)
        self.assertEqual(stats.candidates, 4)
        self.assertEqual([e.line_no for e in stats.rejected], [4, 5])

    def test_strict_stops_on_first_error(self):
        with self.assertRaises(exc.MalformedRecordError):
            list(parse_stream([line(), "мусор", line()], strict=True))


class AnalyticsTest(unittest.TestCase):
    def setUp(self):
        rows = [
            line("TMP-001", "0x0000", "40"),
            line("TMP-001", "0x0001", "90"),
            line("TMP-002", "0x0000", "50"),
            line("VLT-001", "0x0002", "10.5"),
            line("VLT-001", "0x0000", "12.0"),
            line("FAN-001", "0x0010", "4000"),
        ]
        self.records = list(parse_stream(rows))

    def test_filter_by_kind_and_node(self):
        got = list(filter_records(self.records, kinds=["TMP"]))
        self.assertEqual(len(got), 3)
        got = list(filter_records(self.records, nodes={"VLT-001"}))
        self.assertEqual(len(got), 2)

    def test_filter_critical_and_limits(self):
        self.assertEqual(
            len(list(filter_records(self.records, critical_only=True))), 2)
        got = list(filter_records(self.records, min_value=45,
                                  max_value=100))
        self.assertEqual({s.node_id for s in got}, {"TMP-001", "TMP-002"})

    def test_filter_custom_predicate_and_time(self):
        got = list(filter_records(
            self.records, lambda s: s.value > 1000,
            since=datetime(2026, 1, 1)))
        self.assertEqual(len(got), 1)
        self.assertEqual(len(list(filter_records(
            self.records, until=datetime(2020, 1, 1)))), 0)

    def test_filter_rejects_unknown_limit(self):
        with self.assertRaises(TypeError):
            list(filter_records(self.records, bogus=1))

    def test_records_must_be_positional(self):
        with self.assertRaises(TypeError):
            list(filter_records(records=self.records))

    def test_aggregate(self):
        agg = aggregate(self.records)
        self.assertEqual(agg.total, 6)
        self.assertEqual(agg.nodes, {"TMP-001", "TMP-002", "VLT-001",
                                     "FAN-001"})
        self.assertEqual(agg.critical_nodes, {"TMP-001", "VLT-001"})
        self.assertEqual(len(agg.critical_events), 2)
        self.assertEqual(agg.flag_histogram,
                         Counter({"OVER_TEMP": 1, "UNDER_VOLTAGE": 1,
                                  "LINK_DOWN": 1}))
        first = agg.stats[0]
        self.assertEqual(first.node_id, "FAN-001")   # відсортовано
        tmp1 = next(s for s in agg.stats if s.node_id == "TMP-001")
        self.assertEqual((tmp1.count, tmp1.minimum, tmp1.maximum,
                          tmp1.mean), (2, 40.0, 90.0, 65.0))
        self.assertEqual(tmp1.flags_seen, 0x0001)
        self.assertEqual(tmp1.critical_count, 1)

    def test_flags_are_united_across_records(self):
        rows = [line("TMP-001", "0x0001"), line("TMP-001", "0x0010"),
                line("TMP-001", "0x0040")]
        stats = aggregate(parse_stream(rows)).stats[0]
        self.assertEqual(stats.flags_seen, 0x0051)

    def test_aggregate_empty(self):
        agg = aggregate(iter(()))
        self.assertEqual((agg.total, agg.stats), (0, ()))

    def test_node_stats_are_immutable(self):
        stats = aggregate(self.records).stats[0]
        with self.assertRaises(AttributeError):
            stats.count = 99


if __name__ == "__main__":
    unittest.main()