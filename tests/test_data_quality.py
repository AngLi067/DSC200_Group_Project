import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from audit_data import run_audit
from retailrocket_tools.contracts import SCHEMAS
from retailrocket_tools.io import fingerprint, read_rows, write_json
from retailrocket_tools.validation import ValidationError, validate


class DataQualityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.raw = self.root / "raw"
        self.raw.mkdir()
        self.output = self.root / "quality"
        self.events = [
            [10, 0, "view", 10, ""], [20, 0, "addtocart", 10, ""],
            [30, 1, "view", 20, ""], [40, 1, "transaction", 30, 7],
        ]
        self.write("events.csv", self.events)
        self.write("category_tree.csv", [[1, ""]])
        self.write("item_properties_part1.csv", [[5, 10, "available", 1],
                   [25, 10, "available", 0], [5, 10, "categoryid", 99]])
        self.write("item_properties_part2.csv", [[5, 20, "available", 1]])

    def write(self, name, records):
        with (self.raw / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(SCHEMAS[name])
            writer.writerows(records)

    def report(self):
        return json.loads((self.output / "audit_report.json").read_text())

    def test_valid_zero_ids_structural_nulls_and_exact_profile(self):
        before = {p.name: p.read_bytes() for p in self.raw.iterdir()}
        report = run_audit(self.raw, self.output)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["validation"]["failed_checks"], 0)
        self.assertEqual(report["validation"]["warning_checks"], 1)
        profile = report["profile"]
        self.assertEqual((profile["events"], profile["visitors"], profile["event_items"]), (4, 2, 3))
        self.assertEqual(profile["event_counts"], {"view": 2, "addtocart": 1, "transaction": 1})
        self.assertEqual(profile["event_timestamp_range_ms"], [10, 40])
        self.assertEqual(profile["events_per_visitor"]["median"], 2)
        self.assertEqual(profile["availability_record_states"], {"1": 2, "0": 1})
        self.assertAlmostEqual(profile["any_time_item_availability_coverage"], 2 / 3)
        self.assertEqual(profile["event_items_without_any_availability_history"], 1)
        for name, original in before.items():
            self.assertEqual((self.raw / name).read_bytes(), original)
            self.assertEqual(report["input_manifest"][name]["sha256"], hashlib.sha256(original).hexdigest())

    def test_failed_rerun_replaces_old_success_report(self):
        first = run_audit(self.raw, self.output)
        (self.raw / "events.csv").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "Required file not found"):
            run_audit(self.raw, self.output)
        failed = self.report()
        self.assertEqual(failed["status"], "failed")
        self.assertNotEqual(first["run_id"], failed["run_id"])
        self.assertNotIn("profile", failed)
        self.assertEqual(failed["error"]["type"], "FileNotFoundError")

    def test_invalid_values_count_failures_and_bound_examples(self):
        self.write("events.csv", [[i, 0, "click", 10, ""] for i in range(20)])
        with self.assertRaises(ValidationError):
            run_audit(self.raw, self.output)
        check = next(c for c in self.report()["validation"]["checks"] if c["check"] == "events.csv.fields")
        self.assertEqual(check["failure_count"], 20)
        self.assertEqual(len(check["examples"]), 5)

    def test_invalid_numeric_and_transaction_fields_are_rejected(self):
        for row in [
            ["1.5", 0, "view", 10, ""], [10, -1, "view", 10, ""],
            [10, 2**31, "view", 10, ""], [10, 0, "transaction", 10, ""],
            [10, 0, "view", 10, "NaN"],
        ]:
            with self.subTest(row=row):
                self.write("events.csv", [row])
                checks, _ = validate(self.raw)
                self.assertFalse(checks["passed"])

    def test_invalid_availability_and_conflicting_updates_are_rejected(self):
        for records in [
            [[5, 10, "available", 2]],
            [[5, 20, "available", 0]],  # Conflicts with part2 at exactly the same timestamp.
        ]:
            with self.subTest(records=records):
                self.write("item_properties_part1.csv", records)
                with self.assertRaises(ValidationError):
                    run_audit(self.raw, self.output)
                self.assertEqual(self.report()["status"], "failed")

    def test_identical_availability_records_are_warning_not_conflict(self):
        self.write("item_properties_part1.csv", [[5, 20, "available", 1]])
        report = run_audit(self.raw, self.output)
        check = next(c for c in report["validation"]["checks"] if c["check"] == "availability.repeated_states")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(check["failure_count"], 1)
        self.assertEqual(check["severity"], "warning")

    def test_duplicate_category_ids_and_empty_events_are_rejected(self):
        self.write("category_tree.csv", [[1, ""], [1, ""]])
        self.write("events.csv", [])
        checks, _ = validate(self.raw)
        failures = {c["check"] for c in checks["checks"] if not c["passed"]}
        self.assertIn("category_tree.unique_ids", failures)
        self.assertIn("events.csv.nonempty", failures)

    def test_output_inside_raw_directory_is_rejected_without_source_writes(self):
        for output in (self.raw, self.raw / "quality"):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "outside the raw"):
                run_audit(self.raw, output)
        self.assertEqual(set(p.name for p in self.raw.iterdir()), set(SCHEMAS))

    def test_source_changes_during_audit_are_detected(self):
        def changing_validate(directory):
            result = validate(directory)
            with (directory / "events.csv").open("a") as stream:
                stream.write("\n")
            return result
        with patch("audit_data.validate", side_effect=changing_validate):
            with self.assertRaisesRegex(ValueError, "Source file changed during audit"):
                run_audit(self.raw, self.output)
        self.assertEqual(self.report()["status"], "failed")

    def test_reporting_error_does_not_mask_original_failure(self):
        (self.raw / "events.csv").unlink()
        def failing_report(path, value):
            if value["status"] == "failed":
                raise OSError("simulated disk failure")
            write_json(path, value)
        with patch("audit_data.write_json", side_effect=failing_report):
            with self.assertRaises(FileNotFoundError) as raised:
                run_audit(self.raw, self.output)
        self.assertIn("simulated disk failure", raised.exception.__notes__[0])
        self.assertEqual(self.report()["status"], "running")


class DataIOTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_atomic_json_preserves_previous_file_on_failure_and_cleans_temporary(self):
        path = self.root / "report.json"
        write_json(path, {"previous": True})
        with self.assertRaises(ValueError):
            write_json(path, {"value": float("nan")})
        with patch("retailrocket_tools.io.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                write_json(path, {"new": True})
        self.assertEqual(json.loads(path.read_text()), {"previous": True})
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_fingerprints_handle_empty_and_unterminated_files(self):
        path = self.root / "events.csv"
        for content, lines in [(b"", 0), (b"header", 1), (b"header\nrow", 2), (b"header\nrow\n", 2)]:
            with self.subTest(content=content):
                path.write_bytes(content)
                result = fingerprint(path)
                self.assertEqual(result["physical_lines"], lines)
                self.assertEqual(result["bytes"], len(content))
                self.assertEqual(result["sha256"], hashlib.sha256(content).hexdigest())

    def test_bom_and_reordered_columns_are_supported(self):
        path = self.root / "category_tree.csv"
        path.write_text("\ufeffparentid,categoryid\n,0\n", encoding="utf-8")
        self.assertEqual(list(read_rows(path)), [(2, {"parentid": "", "categoryid": "0"})])

    def test_malformed_header_and_ragged_rows_are_rejected(self):
        path = self.root / "category_tree.csv"
        for content in ["categoryid,categoryid\n1,1\n", "categoryid\n1\n",
                        "categoryid,parentid\n1\n", 'categoryid,parentid\n"1,\n']:
            with self.subTest(content=content):
                path.write_text(content)
                with self.assertRaises((ValueError, csv.Error)):
                    list(read_rows(path))


if __name__ == "__main__":
    unittest.main()
