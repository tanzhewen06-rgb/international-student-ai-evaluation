"""Offline integration checks. Never calls an API or writes historical runs."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import runner


def args(**overrides):
    values = dict(batch="batch_007", run="run_20261029T054348.161406Z_V4.12_cbf37824",
                  target="gpt-5.4-nano", judge="deepseek-flash", scenario="scenario_5",
                  repeat=2, response_id=None, dimensions="all", allow_rejudge=False)
    values.update(overrides)
    return SimpleNamespace(**values)


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = runner.prepare(LIVE, args())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/"Evaluation Agent"
        self.case = dict(self.prepared)
        cm = copy.deepcopy(self.prepared["comparison_manifest"])
        self.case.update(root=self.root, comparison=self.root/"evaluations"/cm["evaluation_batch"]/"comparison"/"original",
                         comparison_manifest=cm)
        for outcome in cm["outcomes"]:
            old = Path(outcome["output_dir"])
            new = self.root/"evaluations"/cm["evaluation_batch"]/old.parent.name/old.name
            new.mkdir(parents=True)
            for p in old.iterdir():
                if p.is_file():
                    shutil.copyfile(p, new/p.name)
            outcome["output_dir"] = str(new)
            if old == self.prepared["pair"]:
                self.case["pair"] = new
        self.original = {p: runner.sha(p.read_bytes()) for p in self.root.rglob("*") if p.is_file()}
        self.calls = []

    def fake(self, *request):
        self.calls.append(request)
        return {"text": json.dumps({"checks": [True]*4, "issues": [],
                "dimensions": {f"D{i}": {"anchor": 10, "comment": "Offline simulated judgment."} for i in range(1, 7)}}),
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}

    def assert_originals(self):
        self.assertTrue(all(p.exists() and runner.sha(p.read_bytes()) == h for p, h in self.original.items()))

    def test_default_exact_target_and_hashes(self):
        self.assertEqual(self.case["source"]["record"]["response_id"], "be3e9b64d51549a6b78bd285b7886fd4")
        self.assertEqual(self.case["hashes"], self.case["manifest"]["initial_request_hashes"][self.case["source"]["record"]["response_id"]])

    def test_complete_recovery_combines_100_scores(self):
        result = runner.execute(self.case, call_fn=self.fake)
        self.assertEqual(result["status"], "scored")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][1:], (self.case["task"], self.case["instructions"]))
        combined = runner.read_json(result["summary"].with_name("effective_scores.json"))
        self.assertEqual(len(combined), 100)
        self.assertEqual(sum(r["status"] == "complete" for r in combined), 100)
        self.assert_originals()

    def test_partial_does_not_fill_other_dimensions(self):
        self.case["dimensions"] = [runner.DIMENSIONS[5]]
        result = runner.execute(self.case, call_fn=self.fake)
        row = runner.effective_pair(self.case["pair"], self.case["manifest"])[self.case["source"]["record"]["response_id"]]
        self.assertEqual(row["status"], "partial")
        self.assertEqual(set(row["dimensions"]), {runner.DIMENSIONS[5]})
        self.assertEqual(len(runner.rows(result["folder"]/"judgment.jsonl")[0]["dimensions"]), 6)
        self.assert_originals()

    def test_selected_dimension_only_replaces_existing_score(self):
        first = runner.execute(self.case, call_fn=self.fake)
        before = runner.effective_pair(self.case["pair"], self.case["manifest"])
        self.case.update(dimensions=[runner.DIMENSIONS[5]], allow_rejudge=True)
        def lower(*request):
            value = self.fake(*request)
            raw = json.loads(value["text"])
            for dim in raw["dimensions"].values(): dim["anchor"] = 7
            value["text"] = json.dumps(raw)
            return value
        second = runner.execute(self.case, call_fn=lower)
        self.assertEqual(second["status"], "scored")
        rid = self.case["source"]["record"]["response_id"]
        after = runner.effective_pair(self.case["pair"], self.case["manifest"])
        for d in runner.DIMENSIONS[:5]: self.assertEqual(before[rid]["dimensions"][d], after[rid]["dimensions"][d])
        self.assertEqual(after[rid]["dimensions"][runner.DIMENSIONS[5]]["score"], 7)

    def test_duplicate_blocks_before_request(self):
        runner.execute(self.case, call_fn=self.fake)
        with self.assertRaisesRegex(ValueError, "already supplemented"):
            runner.execute(self.case, call_fn=self.fake)
        self.assertEqual(len(self.calls), 1)

    def test_invalid_output_has_two_attempts_and_no_accepted_patch(self):
        def bad(*request): self.calls.append(request); return "not json"
        result = runner.execute(self.case, call_fn=bad)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(len(self.calls), 2)
        self.assertFalse((result["folder"]/"accepted_patch.json").exists())
        self.assertEqual(runner.effective_pair(self.case["pair"], self.case["manifest"])[self.case["source"]["record"]["response_id"]]["status"], "missing")
        self.assert_originals()

    def test_provider_error_sanitized_and_no_retry(self):
        def bad(*request): self.calls.append(request); raise RuntimeError("secret-api-token")
        result = runner.execute(self.case, call_fn=bad)
        self.assertEqual(result["status"], "evaluation_error")
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("secret-api-token", (result["folder"]/"errors.jsonl").read_text())
        self.assertFalse((self.case["pair"]/".single_item_patch.lock").exists())
        self.assert_originals()

    def test_existing_lock_blocks_request(self):
        lock = self.case["pair"]/".single_item_patch.lock"
        lock.write_text("another run")
        with self.assertRaisesRegex(ValueError, "already running"):
            runner.execute(self.case, call_fn=self.fake)
        self.assertEqual(self.calls, [])
        self.assertTrue(lock.exists())

    def test_exports_can_be_rebuilt_without_call(self):
        with patch.object(runner, "refresh_comparison", side_effect=OSError("test disk error")):
            result = runner.execute(self.case, call_fn=self.fake)
        self.assertTrue(result["export_pending"])
        self.assertTrue((result["folder"]/"accepted_patch.json").exists())
        csv = runner.refresh_comparison(self.case, "offline_refresh")
        self.assertTrue(csv.exists())
        self.assertEqual(len(self.calls), 1)

    def test_score_status_provisional_retained(self):
        def provisional(*request):
            value = self.fake(*request); raw = json.loads(value["text"])
            raw["issues"] = [{"kind": "unsupported_assertion", "quote": "An absent quotation.",
                             "why": "A factual premise affects advice.", "impacts": {"D6": "material"}, "materiality": []}]
            value["text"] = json.dumps(raw)
            return value
        result = runner.execute(self.case, call_fn=provisional)
        accepted = runner.read_json(result["folder"]/"accepted_patch.json")
        self.assertEqual(accepted["dimensions"][runner.DIMENSIONS[5]]["score_status"], "provisional")
        self.assertEqual(accepted["dimensions"][runner.DIMENSIONS[5]]["score"], 6)

    def test_selectors_and_dimensions_reject_invalid_values(self):
        for overrides in ({"scenario": "scenario_99"}, {"response_id": "wrong"}, {"target": "missing"},
                          {"dimensions": ["D7"]}, {"dimensions": ["D6", "D6"]}, {"batch": "../elsewhere"}):
            with self.subTest(overrides=overrides), self.assertRaises((ValueError, FileNotFoundError)):
                runner.prepare(LIVE, args(**overrides))

    def test_scored_record_requires_explicit_rejudge(self):
        with self.assertRaisesRegex(ValueError, "already has a score"):
            runner.prepare(LIVE, args(scenario="scenario_1", repeat=1))

    def test_snapshot_and_code_hash_mismatch_blocks_preparation(self):
        original = runner.sha
        with patch.object(runner, "sha", side_effect=lambda raw: "0"*64):
            with self.assertRaisesRegex(ValueError, "Scoring code changed"):
                runner.prepare(LIVE, args())


if __name__ == "__main__":
    unittest.main(verbosity=2)
