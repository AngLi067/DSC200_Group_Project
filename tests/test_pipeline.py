"""CLI functional tests using an offline, hand-verifiable Retailrocket fixture."""

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from scipy.sparse import load_npz


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw"
        self.processed = self.root / "processed"
        self.outputs = self.root / "outputs"
        self.raw.mkdir()
        self.events = [
            [10, 1, "view", 10, ""],
            [10, 1, "addtocart", 10, ""],
            [20, 1, "transaction", 20, 1],
            [30, 2, "view", 20, ""],
            [40, 2, "view", 30, ""],
            [50, 1, "view", 40, ""],
            [60, 1, "view", 10, ""],
            [70, 1, "view", 30, ""],
            [80, 1, "view", 20, ""],
            [90, 2, "transaction", 50, 2],
        ]
        # Unsorted input proves the split follows time, not file order.
        self.write_events(list(reversed(self.events)))
        self.write_csv("item_properties_part1.csv", ["timestamp", "itemid", "property", "value"], [
            [0, 10, "available", 1], [75, 10, "available", 0],
            [0, 20, "available", 0], [85, 20, "available", 1],
        ])
        self.write_csv("item_properties_part2.csv", ["timestamp", "itemid", "property", "value"], [
            [0, 40, "available", 1], [0, 50, "available", 1], [0, 10, "categoryid", 1],
        ])
        self.write_csv("category_tree.csv", ["categoryid", "parentid"], [[1, ""]])

    def write_csv(self, filename, header, rows):
        with (self.raw / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)

    def write_events(self, rows):
        self.write_csv("events.csv", ["timestamp", "visitorid", "event", "itemid", "transactionid"], rows)

    def run_cli(self, script, *args, succeeds=True):
        result = subprocess.run(
            [sys.executable, str(ROOT / script), *map(str, args)],
            cwd=ROOT, text=True, capture_output=True, timeout=60,
        )
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def prepare(self):
        self.run_cli("prepare_data.py", self.raw, "--output-dir", self.processed)

    def test_f01_offline_acquisition_audit_and_temporal_preparation(self):
        destination = self.root / "copied"
        self.run_cli("download_dataset.py", "--source-dir", self.raw, "--output-dir", destination)
        for source in self.raw.glob("*.csv"):
            self.assertEqual(source.read_bytes(), (destination / source.name).read_bytes())
        self.run_cli("audit_data.py", destination, "--output-dir", self.root / "quality")
        quality = json.loads((self.root / "quality" / "audit_report.json").read_text())
        self.assertEqual(quality["status"], "passed")
        self.assertEqual(quality["profile"]["events"], 10)
        self.run_cli("prepare_data.py", destination, "--output-dir", self.processed)
        metadata = json.loads((self.processed / "metadata.json").read_text())
        self.assertEqual(metadata["cutoff_timestamp_ms"], 72)
        self.assertEqual((metadata["train_events"], metadata["test_events"]), (8, 2))
        self.assertEqual(metadata["train_catalog_items"], 4)
        np.testing.assert_array_equal(np.load(self.processed / "item_ids.npy"), [10, 20, 30, 40, 50])
        np.testing.assert_array_equal(np.load(self.processed / "availability_at_cutoff.npy"), [1, 0, -1, 1, 1])
        np.testing.assert_array_equal(load_npz(self.processed / "train_interactions.npz").toarray(), [
            [5, 5, 1, 1, 0], [0, 1, 1, 0, 0],
        ])
        np.testing.assert_array_equal(load_npz(self.processed / "test_targets.npz").toarray(), [
            [0, 1, 0, 0, 0], [0, 0, 0, 0, 1],
        ])

    def test_f02_two_model_evaluation_with_small_catalog(self):
        self.prepare()
        self.run_cli("recommendation_models.py", self.processed, "--output-dir", self.outputs,
                     "--k", 6, "--candidate-k", 8, "--neighbors", 2, "--threads", 1)
        for name in ("popularity", "item_based_cosine"):
            model_dir = self.outputs / name
            raw = np.load(model_dir / "raw_recommendations.npy")
            filtered = np.load(model_dir / "filtered_recommendations.npy")
            self.assertEqual(raw.shape, (2, 6))
            self.assertEqual(filtered.shape, (2, 6))
            for row in raw:
                self.assertEqual(set(row[row >= 0]), {10, 20, 30, 40})
                self.assertEqual(np.count_nonzero(row >= 0), 4)
            for row in filtered:
                self.assertEqual(set(row[row >= 0]), {10, 30, 40})
                self.assertEqual(np.count_nonzero(row >= 0), 3)
            metrics = json.loads((model_dir / "metrics.json").read_text())
            self.assertEqual(metrics["raw"]["recall@6"], 0.5)
            self.assertEqual(metrics["raw"]["unavailable_recommendation_rate"], 0.25)
            self.assertEqual(metrics["known_unavailable_filtered"]["unavailable_recommendation_rate"], 0.0)
            self.assertEqual(metrics["known_unavailable_filtered"]["recall@6"], 0.0)
            self.assertEqual(metrics["known_unavailable_filtered"]["recommendation_slots_filled"], 6)
        pop = np.load(self.outputs / "popularity" / "raw_recommendations.npy")
        np.testing.assert_array_equal(pop, [[20, 10, 30, 40, -1, -1]] * 2)
        summary = json.loads((self.outputs / "evaluation_summary.json").read_text())
        self.assertEqual(summary["parameters"], {"k": 6, "candidate_k": 8, "neighbors": 2, "threads": 1})
        self.assertEqual(summary["users_evaluated"], 2)
        self.assertIn("implicit", summary["environment"])

    def test_f03_invalid_inputs_fail_without_success_metrics(self):
        result = self.run_cli("prepare_data.py", self.raw, "--train-fraction", 1, succeeds=False)
        self.assertIn("--train-fraction", result.stderr)
        result = self.run_cli("recommendation_models.py", self.processed, "--output-dir", self.outputs,
                              "--k", 10, "--candidate-k", 5, succeeds=False)
        self.assertIn("candidate-k must be >= k", result.stderr)
        (self.raw / "events.csv").unlink()
        result = self.run_cli("audit_data.py", self.raw, "--output-dir", self.root / "quality", succeeds=False)
        self.assertIn("Required file not found", result.stderr)
        self.assertFalse((self.outputs / "evaluation_summary.json").exists())

    def test_identical_timestamps_cannot_create_a_test_partition(self):
        self.write_events([[10, 1, "view", 10, ""], [10, 1, "view", 20, ""]])
        result = self.run_cli("prepare_data.py", self.raw, "--output-dir", self.processed, succeeds=False)
        self.assertIn("both sides of the cutoff", result.stderr)
        self.assertFalse((self.processed / "metadata.json").exists())

    def test_no_evaluable_users_is_reported_before_writing_results(self):
        self.write_events([[10, 1, "view", 10, ""], [20, 2, "view", 20, ""]])
        self.prepare()
        result = self.run_cli("recommendation_models.py", self.processed,
                              "--output-dir", self.outputs, succeeds=False)
        self.assertIn("No test users", result.stderr)
        self.assertFalse(self.outputs.exists())

    def test_audit_rejects_unknown_event_type(self):
        self.write_events([[10, 1, "click", 10, ""]])
        result = self.run_cli("audit_data.py", self.raw, "--output-dir", self.root / "quality", succeeds=False)
        self.assertIn("Unknown event type", result.stderr)


if __name__ == "__main__":
    unittest.main()
