"""Regression tests for restart integrity, source provenance, and opening inputs."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import common
from common import ROOT, digest
from execution import open_experiment, read_checkpoint
from futures import external_paths


class RestartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.spec = {'format_version': 1, 'simulation': {'code': 'A', 'source': 'A', 'dependencies': 'A'},
                     'futures_sha256': 'A', 'future_ids': ['f0'],
                     'settings': {'policies': {'p': {'cash': 12}}, 'mode': 'normal'}}

    def tearDown(self):
        self.temp.cleanup()

    def record(self):
        path, fingerprint, _ = open_experiment(self.directory, 'test', self.spec)
        record = {'future_id': 'f0', 'experiment_sha256': fingerprint,
                  'rows': [{'future_id': 'f0', 'policy': 'p', 'funded': True}]}
        record['record_sha256'] = digest(record)
        path.write_text(json.dumps(record)+'\n')
        return path, fingerprint, record

    def test_matching_resume_accepts_completed_future(self):
        self.record()
        self.assertEqual(len(open_experiment(self.directory, 'test', self.spec)[2]), 1)

    def test_changed_input_policy_code_source_and_environment_are_rejected(self):
        self.record()
        for key in ['code', 'source', 'dependencies', 'futures', 'policy', 'mode']:
            changed = deepcopy(self.spec)
            if key in changed['simulation']: changed['simulation'][key] = 'B'
            elif key == 'futures': changed['futures_sha256'] = 'B'
            elif key == 'policy': changed['settings']['policies']['p']['cash'] = 18
            else: changed['settings']['mode'] = 'tail'
            with self.subTest(change=key), self.assertRaisesRegex(RuntimeError, 'Experiment changed'):
                open_experiment(self.directory, 'test', changed)

    def test_legacy_checkpoint_is_not_adopted(self):
        (self.directory/'legacy.jsonl').write_text('{"future_id":"f0"}\n')
        with self.assertRaisesRegex(RuntimeError, 'no matching experiment manifest'):
            open_experiment(self.directory, 'legacy', self.spec)

    def test_tampered_record_is_rejected(self):
        path, fingerprint, record = self.record()
        record['rows'][0]['funded'] = False
        path.write_text(json.dumps(record)+'\n')
        with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
            read_checkpoint(path, fingerprint, {'f0'})

    def test_truncated_record_is_rejected(self):
        path, fingerprint, _ = self.record()
        with path.open('a') as stream: stream.write('{"future_id":')
        with self.assertRaisesRegex(RuntimeError, 'Incomplete or damaged'):
            read_checkpoint(path, fingerprint, {'f0'})

    def test_duplicate_and_foreign_futures_are_rejected(self):
        path, fingerprint, record = self.record()
        with path.open('a') as stream: stream.write(json.dumps(record)+'\n')
        with self.assertRaisesRegex(RuntimeError, 'duplicate'):
            read_checkpoint(path, fingerprint, {'f0'})
        path.write_text(json.dumps(record)+'\n')
        with self.assertRaisesRegex(RuntimeError, 'Unknown'):
            read_checkpoint(path, fingerprint, {'different_future'})

    def test_checkpoint_fingerprint_and_path_traversal_are_rejected(self):
        path, _, _ = self.record()
        with self.assertRaisesRegex(RuntimeError, 'fingerprint mismatch'):
            read_checkpoint(path, 'different', {'f0'})
        with self.assertRaises(ValueError):
            open_experiment(self.directory, '../outside', self.spec)


class SourceAndOpeningTests(unittest.TestCase):
    def test_wrong_source_commit_rejected(self):
        with patch('common.subprocess.check_output', return_value='different\n'):
            with self.assertRaisesRegex(RuntimeError, 'Source commit mismatch'):
                common.check_source()

    def test_changed_dependency_rejected(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'evidence').mkdir()
            file = root/'source.py'; file.write_text('original')
            (root/'evidence/source_dependencies.json').write_text(json.dumps({'files': {'source.py': hashlib.sha256(file.read_bytes()).hexdigest()}}))
            with patch('common.ROOT', root), patch('common.subprocess.check_output', return_value=common.SOURCE_COMMIT):
                common.check_source(root)
                file.write_text('modified')
                with self.assertRaisesRegex(RuntimeError, 'missing or changed'):
                    common.check_source(root)

    def test_prices_valuation_and_fx_follow_supplied_opening(self):
        futures = json.loads((ROOT/'inputs/futures_main.json').read_text())
        original = common.source_base()['initial_point']
        changed = deepcopy(original)
        changed['btc_price_usd'] = common.opening_market(original)['price']*2
        changed['multiple'] *= 1.25
        changed['fx_usd_per_unit']['EUR'] *= 1.1
        for f in futures[:2]:  # historical-block and stylized families
            a = external_paths(f, original); b = external_paths(f, changed)
            np.testing.assert_array_equal(b['price'], a['price']*2)
            np.testing.assert_allclose(b['multiple'], a['multiple']*1.25, rtol=1e-14)
            np.testing.assert_allclose(b['fx'], a['fx']*1.1, rtol=1e-14)


if __name__ == '__main__':
    unittest.main(verbosity=2)
