"""Offline privacy and data-location checks; no model API calls."""
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Evaluation Agent'))
from runtime import configured_evaluation as evaluation
from runtime import missing_scores, portable_json
from runtime.paths import RESPONSES_ROOT, EVALUATIONS_ROOT, path_key, relocated_path
from runtime.storage import append_record, read_sources


class PortableProject(unittest.TestCase):
    def setUp(self):
        def forbidden(*args, **kwargs):
            raise AssertionError('Network calls are forbidden in offline tests.')
        self.patch_connect = patch.object(socket.socket, 'connect', forbidden)
        self.patch_connection = patch.object(socket, 'create_connection', forbidden)
        self.patch_connect.start()
        self.patch_connection.start()
        self.addCleanup(self.patch_connect.stop)
        self.addCleanup(self.patch_connection.stop)

    def test_json_paths_and_dictionary_keys_round_trip(self):
        file = RESPONSES_ROOT / 'Final_Batch_Type_1/responses_gpt-6.1-sol.jsonl'
        original = {'source_file': str(file), 'source_file_sha256': {str(file): 'abc'}}
        text = portable_json.dumps(original)
        self.assertIn('project://Sample Data/responses/', text)
        self.assertNotIn(str(ROOT), text)
        restored = portable_json.loads(text)
        self.assertEqual(path_key(restored['source_file']), path_key(file))
        self.assertEqual(path_key(next(iter(restored['source_file_sha256']))), path_key(file))

    def test_real_metadata_writers_use_relative_paths(self):
        original = {'source_file': str(RESPONSES_ROOT / 'batch_001/responses_gpt-6.1-sol.jsonl')}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            evaluation.write_json(folder / 'manifest.json', original)
            append_record(folder / 'records.jsonl', original)
            for path in folder.iterdir():
                text = path.read_text(encoding='utf-8')
                self.assertIn('project://Sample Data/responses/', text)
                self.assertNotIn(str(ROOT), text)

    def test_project_references_cannot_escape_the_root(self):
        for value in ('project://../private.txt', 'project:///private.txt', 'project://file:private.txt'):
            with self.assertRaises(ValueError):
                relocated_path(value)

    def test_completed_dataset_is_readable_at_this_location(self):
        batch = RESPONSES_ROOT / 'Final_Batch_Type_1'
        sources = sorted(batch.glob('responses_*.jsonl'))
        self.assertEqual(len(sources), 5)
        answers, errors = read_sources(batch, source_files=sources)
        self.assertFalse(errors)
        self.assertEqual(len(answers), 125)
        trial = EVALUATIONS_ROOT / 'Final_Batch_Type_1/judge_comparison_v4_17/trial_20261102T211905.670197Z_251b2721'
        manifest = evaluation.read_json(trial / 'trial_manifest.json')
        _, effective, _ = missing_scores._collect(trial, manifest)
        self.assertEqual(len(effective), 375)
        self.assertTrue(all(row['status'] == 'scored' for row in effective.values()))
        self.assertEqual(sum(row.get('score_status') == 'provisional' for row in effective.values()), 5)


if __name__ == '__main__':
    unittest.main()
