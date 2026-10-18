"""Single entry point for engine, policy, transaction, and restart regression checks."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import pandas as pd
from common import ROOT, EXTENSION_VERSION, write_json, source_identity
from execution import simulation_identity


def command(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True, cwd=ROOT,
                   env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))


def main():
    if not __debug__:
        raise RuntimeError('Run verification without Python -O; assertion checks must remain enabled.')
    started = time.time()
    source_identity()
    command(ROOT/'test_release.py')
    command(ROOT/'verify.py')
    command(ROOT/'audit_witnesses.py')
    # A real CLI run, a no-op resume, and parity against retained release 1.0.
    with tempfile.TemporaryDirectory(prefix='rdm_release_smoke_') as directory:
        policies = ['bps_100', 'liquidity_cap', 'anticipatory_12', 'anticipatory_sale']
        args = [ROOT/'run_study.py', '--phase', 'main', '--limit', '4', '--workers', '2',
                '--policies', *policies, '--output-dir', directory, '--tag', 'smoke']
        command(*args)
        file = Path(directory)/'smoke.csv'
        first_hash = hashlib.sha256(file.read_bytes()).hexdigest()
        command(*args)
        if hashlib.sha256(file.read_bytes()).hexdigest() != first_hash:
            raise AssertionError('An unchanged resume changed exported results.')
        run = json.loads((Path(directory)/'smoke_run.json').read_text())
        if run['new_futures'] != 0:
            raise AssertionError('An unchanged resume reran completed futures.')
        # Compare original exports, avoiding an extra parse/write cycle in the
        # assembled all_main table, and preserve round-trip float precision.
        retained = pd.concat([pd.read_csv(ROOT/'outputs'/name, float_precision='round_trip',dtype={'first_stop_date':'string'})
                              for name in ['main_normal.csv','main_revisions.csv']],ignore_index=True)
        actual = pd.read_csv(file, float_precision='round_trip',dtype={'first_stop_date':'string'})
        keys = ['future_id','policy','horizon','variant']
        expected = retained[retained.future_id.isin(actual.future_id)&retained.policy.isin(policies)]
        expected = expected.set_index(keys).sort_index()[actual.set_index(keys).columns]
        # CSV inference can label an all-zero subset as integer and the full
        # table as float. Require identical values, not identical inferred dtypes.
        pd.testing.assert_frame_equal(actual.set_index(keys).sort_index(), expected, check_exact=True,check_dtype=False)
        command(ROOT/'replay.py', 'main_0003', 'anticipatory_sale', '--out', Path(directory)/'replay.json.gz')
    report = dict(passed=True,extension_version=EXTENSION_VERSION,simulation=simulation_identity(),
                  checks=['restart and source regression suite','original and revised engine verification',
                          'independent transaction witnesses','fresh CLI execution and no-op resume',
                          'exact parity of 64 retained checkpoint rows','full ledger replay with retained configuration hash'],
                  elapsed_seconds=time.time()-started)
    write_json(ROOT/'outputs/release_verification.json', report)
    print(json.dumps({'release_verification_passed': True, 'seconds': report['elapsed_seconds']},indent=2))


if __name__ == '__main__':
    main()
