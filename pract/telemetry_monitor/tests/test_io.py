"""Тести файлового вводу-виводу, CLI та наскрізний сценарій."""

import contextlib
import io
import os
import stat
import tempfile
import unittest
from pathlib import Path

from telemetry_monitor import exceptions as exc
from telemetry_monitor.cli import main, process_log
from telemetry_monitor.storage import AtomicWriter, LogReader, open_report

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "sample_telemetry.log"
GOOD = "TMP-001;0x0000;40.0;2026-03-14T10:00:00\n"


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TempDirCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def write(self, name, text, mode="w"):
        """Записує байти як є: без перекладу \\n у \\r\\n на Windows."""
        path = self.dir / name
        data = text if "b" in mode else text.encode("utf-8")
        path.write_bytes(data)
        return path


class StorageTest(TempDirCase):
    def test_reader_streams_lines(self):
        path = self.write("a.log", "x\ny\r\nz")
        with LogReader(path) as reader:
            self.assertEqual(list(reader.lines()), ["x", "y", "z"])

    def test_reader_closes_file_even_on_error(self):
        path = self.write("a.log", "x\n")
        with self.assertRaises(RuntimeError):
            with LogReader(path) as reader:
                handle = reader._handle
                raise RuntimeError("boom")
        self.assertTrue(handle.closed)

    def test_missing_file(self):
        with self.assertRaises(exc.LogNotFoundError):
            with LogReader(self.dir / "nope.log"):
                pass

    def test_directory_instead_of_file(self):
        with self.assertRaises(exc.LogAccessError):
            with LogReader(self.dir):
                pass

    @unittest.skipIf(not hasattr(os, "geteuid") or os.geteuid() == 0,
                     "права доступу не діють для root або на Windows")
    def test_permission_denied(self):
        path = self.write("secret.log", GOOD)
        path.chmod(0)
        self.addCleanup(path.chmod, stat.S_IRUSR | stat.S_IWUSR)
        with self.assertRaises(exc.LogAccessError):
            with LogReader(path):
                pass

    def test_lines_outside_with(self):
        reader = LogReader(self.dir / "x")
        with self.assertRaises(ValueError):
            next(reader.lines())

    def test_invalid_utf8_does_not_crash(self):
        path = self.write("bad.log", GOOD.encode() + b"\xff\xfe\x00bad\n",
                          mode="wb")
        code, out, _ = run_cli(str(path))
        self.assertEqual(code, 0)
        self.assertIn("Відхилено записів:    1", out)

    def test_atomic_writer_commits(self):
        target = self.dir / "sub" / "r.txt"
        with AtomicWriter(target) as fh:
            fh.write("готово\n")
            self.assertFalse(target.exists())   # ще не опубліковано
        self.assertEqual(target.read_text(encoding="utf-8"), "готово\n")
        self.assertEqual([p.name for p in target.parent.iterdir()],
                         ["r.txt"])

    def test_atomic_writer_rolls_back(self):
        target = self.write("r.txt", "старий звіт")
        with self.assertRaises(RuntimeError):
            with AtomicWriter(target) as fh:
                fh.write("пів-")
                raise RuntimeError("збій посеред запису")
        self.assertEqual(target.read_text(encoding="utf-8"), "старий звіт")
        self.assertEqual([p.name for p in self.dir.iterdir()], ["r.txt"])

    def test_atomic_writer_bad_destination(self):
        blocker = self.write("file", "x")
        with self.assertRaises(exc.ReportWriteError):
            with AtomicWriter(blocker / "child.txt"):
                pass

    def test_open_report_stdout(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with open_report(None) as fh:
                fh.write("hello")
        self.assertEqual(out.getvalue(), "hello")


class WindowsFriendlyTest(TempDirCase):
    """Те, що на Windows трапляється постійно."""

    def sample_bytes(self):
        return SAMPLE.read_bytes().replace(b"\r\n", b"\n")

    def test_crlf_line_endings(self):
        path = self.write("crlf.log", self.sample_bytes().replace(
            b"\n", b"\r\n"), mode="wb")
        summary = process_log(str(path))
        self.assertEqual((summary.parse.records,
                          len(summary.parse.rejected)), (66, 8))

    def test_utf8_bom_from_notepad(self):
        path = self.write("bom.log", b"\xef\xbb\xbf" + self.sample_bytes(),
                          mode="wb")
        summary = process_log(str(path))
        self.assertEqual((summary.parse.records,
                          len(summary.parse.rejected)), (66, 8))
        self.assertEqual(summary.parse.skipped, 3)   # BOM не зіпсував #

    def test_cyrillic_path_with_spaces(self):
        folder = self.dir / "Програмування на Python" / "логи"
        folder.mkdir(parents=True)
        log = folder / "журнал телеметрії.log"
        log.write_bytes(self.sample_bytes())
        report = folder / "звіт.txt"
        code, _, err = run_cli(str(log), "-o", str(report))
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Унікальних вузлів:    6",
                      report.read_text(encoding="utf-8"))

    def test_report_is_utf8_without_bom_and_lf(self):
        report = self.dir / "r.txt"
        run_cli(str(SAMPLE), "-o", str(report))
        raw = report.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r\n", raw)
        raw.decode("utf-8")


class ProcessLogTest(TempDirCase):
    def test_sample(self):
        summary = process_log(str(SAMPLE))
        self.assertEqual(summary.parse.records, 66)
        self.assertEqual(len(summary.parse.rejected), 8)
        self.assertEqual(summary.agg.total, 66)
        self.assertEqual(len(summary.agg.critical_events), 5)

    def test_filters_do_not_change_parse_counts(self):
        summary = process_log(str(SAMPLE), kinds=["TMP"])
        self.assertEqual(summary.parse.records, 66)
        self.assertEqual(summary.agg.total, 24)

    def test_threshold(self):
        path = self.write("x.log", GOOD + "мусор\nмусор\n")
        with self.assertRaises(exc.ErrorThresholdExceededError):
            process_log(str(path), max_error_ratio=0.5)
        process_log(str(path), max_error_ratio=0.7)   # не кидає

    def test_strict_raises_record_error(self):
        path = self.write("x.log", GOOD + "мусор\n")
        with self.assertRaises(exc.MalformedRecordError):
            process_log(str(path), strict=True)

    def test_empty_file(self):
        summary = process_log(str(self.write("e.log", "")))
        self.assertEqual((summary.parse.lines, summary.agg.total), (0, 0))
        self.assertEqual(summary.rejected_ratio, 0.0)


class CliTest(TempDirCase):
    def test_stdout_report(self):
        code, out, err = run_cli(str(SAMPLE))
        self.assertEqual((code, err), (0, ""))
        self.assertIn("ЗВІТ ПРО ТЕЛЕМЕТРІЮ", out)
        self.assertIn("OVER_TEMP", out)

    def test_file_report(self):
        target = self.dir / "out" / "report.txt"
        code, out, _ = run_cli(str(SAMPLE), "-o", str(target))
        self.assertEqual(code, 0)
        self.assertIn("Звіт записано", out)
        text = target.read_text(encoding="utf-8")
        self.assertIn("Статистика за вузлами", text)

    def test_filters(self):
        code, out, _ = run_cli(str(SAMPLE), "--kind", "VLT",
                               "--critical-only")
        self.assertEqual(code, 0)
        self.assertIn("Враховано у вибірці:  2", out)

    def test_missing_log_exit_code(self):
        code, _, err = run_cli(str(self.dir / "none.log"))
        self.assertEqual(code, 3)
        self.assertIn("E3001", err)

    def test_strict_exit_code(self):
        code, _, err = run_cli(str(SAMPLE), "--strict")
        self.assertEqual(code, 4)
        self.assertIn("E2001", err)

    def test_threshold_exit_code(self):
        code, _, err = run_cli(str(SAMPLE), "--max-error-ratio", "0.05")
        self.assertEqual(code, 4)
        self.assertIn("E4000", err)

    def test_bad_ratio(self):
        code, _, err = run_cli(str(SAMPLE), "--max-error-ratio", "7")
        self.assertEqual(code, 2)

    def test_argparse_errors_exit_2(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli(str(SAMPLE), "--kind", "XXX")
        self.assertEqual(ctx.exception.code, 2)

    def test_unwritable_report(self):
        blocker = self.write("file", "x")
        code, _, err = run_cli(str(SAMPLE), "-o", str(blocker / "r.txt"))
        self.assertEqual(code, 3)
        self.assertIn("E3003", err)

    def test_closed_pipe_is_not_an_error(self):
        from unittest import mock
        with mock.patch("telemetry_monitor.cli.write_report",
                        side_effect=BrokenPipeError()):
            code, _, err = run_cli(str(SAMPLE))
        self.assertEqual((code, err), (0, ""))

    def test_real_closed_pipe(self):
        import subprocess
        import sys
        proc = subprocess.Popen(
            [sys.executable, "-m", "telemetry_monitor", str(SAMPLE)],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.stdout.readline()
        proc.stdout.close()          # читач пішов, як Select-Object -First
        err = proc.stderr.read()
        proc.stderr.close()
        self.assertEqual(proc.wait(timeout=30), 0)
        self.assertNotIn("помилка".encode("utf-8"), err)

    def test_unexpected_error_is_contained(self):
        from unittest import mock
        with mock.patch("telemetry_monitor.cli.process_log",
                        side_effect=ZeroDivisionError("x")):
            code, _, err = run_cli(str(SAMPLE))
        self.assertEqual(code, 70)
        self.assertIn("внутрішня помилка", err)

    def test_narrow_console_encoding_does_not_crash(self):
        import subprocess
        import sys
        env = dict(os.environ, PYTHONIOENCODING="cp437", PYTHONUTF8="0")
        proc = subprocess.run(
            [sys.executable, "-m", "telemetry_monitor", str(SAMPLE)],
            cwd=ROOT, capture_output=True, env=env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn(b"data", proc.stdout)

    def test_module_entry_point(self):
        import subprocess
        import sys
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "telemetry_monitor", str(SAMPLE)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            env=env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Унікальних вузлів:    6", proc.stdout)


if __name__ == "__main__":
    unittest.main()