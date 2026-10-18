"""Distribution verification with explicit numerical tolerances; frozen code is unchanged."""
from pathlib import Path
import argparse, gzip, hashlib, json, math, os, subprocess, sys, tempfile, time
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'rdm_study'
sys.path.insert(0, str(STUDY))


def command(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True, cwd=ROOT,
                   env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))


def compare_tree(actual, expected, *, rtol, atol, path='', stats=None):
    """Require exact structure, strings, integers and booleans; bound float error."""
    if stats is None:
        stats = {'numeric_differences': 0, 'max_absolute_difference': 0., 'max_relative_difference': 0.}
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            raise AssertionError(f'Dictionary keys differ: {path}')
        for k in expected:
            compare_tree(actual[k], expected[k], rtol=rtol, atol=atol, path=path+'/'+k, stats=stats)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise AssertionError(f'List lengths differ: {path}')
        for i, (a, e) in enumerate(zip(actual, expected)):
            compare_tree(a, e, rtol=rtol, atol=atol, path=f'{path}/{i}', stats=stats)
    elif isinstance(expected, float):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            raise AssertionError(f'Numeric type differs: {path}')
        if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
            raise AssertionError(f'Float outside tolerance: {path}: {actual!r} != {expected!r}')
        if actual != expected:
            diff=abs(actual-expected); stats['numeric_differences']+=1
            stats['max_absolute_difference']=max(stats['max_absolute_difference'],diff)
            stats['max_relative_difference']=max(stats['max_relative_difference'],diff/max(abs(expected),atol))
    elif type(actual) is not type(expected) or actual != expected:
        raise AssertionError(f'Exact field differs: {path}: {actual!r} != {expected!r}')
    return stats


def main():
    if not __debug__:
        raise RuntimeError('Run without Python -O.')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT/'portable_verification.json')
    args=parser.parse_args();started=time.time()
    from common import digest, source_identity
    from execution import simulation_identity
    from model import configuration
    from metrics import independent_checks
    import engine
    source_identity()
    for name in ['test_release.py','verify.py','audit_witnesses.py']:
        command(STUDY/name)
    witnesses=[]
    for policy in ['liquidity_cap','anticipatory_12']:
        with gzip.open(STUDY/'outputs'/f'witness_{policy}.json.gz','rt') as f:
            retained=json.load(f)
        cfg=retained['configuration']
        if digest(cfg)!=retained['input_sha256']:
            raise AssertionError('Retained witness configuration hash mismatch')
        regenerated,_=configuration(cfg['metadata']['rdm_future'],policy)
        cfg_stats=compare_tree(regenerated,cfg,rtol=1e-14,atol=1e-12)
        # Replay the actual retained configuration, whose hash must still match.
        result=engine.run_dated_configuration(cfg,retained['configuration_id'])
        if result.input_sha256!=retained['input_sha256']:
            raise AssertionError('Replayed retained configuration hash mismatch')
        independent_checks(result)
        replay_stats=compare_tree(result.to_dict(),retained,rtol=1e-11,atol=0.002)
        witnesses.append({'policy':policy,'future_id':cfg['metadata']['rdm_future']['future_id'],
                          'retained_configuration_hash_matched':True,
                          'regenerated_configuration_hash_matched':digest(regenerated)==retained['input_sha256'],
                          'configuration_comparison':cfg_stats,'full_ledger_comparison':replay_stats})
    with tempfile.TemporaryDirectory(prefix='rdm_portable_check_') as directory:
        policies=['bps_100','liquidity_cap','anticipatory_12','anticipatory_sale']
        cmd=[STUDY/'run_study.py','--phase','main','--limit','4','--workers','2',
             '--policies',*policies,'--output-dir',directory,'--tag','smoke']
        command(*cmd);file=Path(directory)/'smoke.csv';first_hash=hashlib.sha256(file.read_bytes()).hexdigest()
        command(*cmd)
        if hashlib.sha256(file.read_bytes()).hexdigest()!=first_hash:
            raise AssertionError('No-op restart changed results')
        if json.loads((Path(directory)/'smoke_run.json').read_text())['new_futures']!=0:
            raise AssertionError('No-op restart reran futures')
        retained=pd.concat([pd.read_csv(STUDY/'outputs'/n,float_precision='round_trip',dtype={'first_stop_date':'string'})
                            for n in ['main_normal.csv','main_revisions.csv']],ignore_index=True)
        actual=pd.read_csv(file,float_precision='round_trip',dtype={'first_stop_date':'string'})
        keys=['future_id','policy','horizon','variant']
        expected=retained[retained.future_id.isin(actual.future_id)&retained.policy.isin(policies)].set_index(keys).sort_index()
        actual=actual.set_index(keys).sort_index();expected=expected[actual.columns]
        if len(actual)!=64 or not actual.index.equals(expected.index):
            raise AssertionError('Unexpected smoke-test record keys')
        differences=[]
        # Generated config hashes are reported separately, never treated as floats.
        hash_mismatches=int((actual.config_sha256!=expected.config_sha256).sum())
        for c in actual.columns:
            if c=='config_sha256': continue
            a,e=actual[c],expected[c]
            if pd.api.types.is_float_dtype(a) or pd.api.types.is_float_dtype(e):
                np.testing.assert_allclose(a.to_numpy(float),e.to_numpy(float),rtol=1e-12,atol=1e-10,equal_nan=True,err_msg=c)
                mask=~((a==e)|(a.isna()&e.isna()))
                if mask.any():
                    differences.append({'column':c,'cells':int(mask.sum()),'max_absolute_difference':float((a-e).abs().max())})
            else:
                pd.testing.assert_series_equal(a,e,check_exact=True,check_dtype=False)
    report={'passed':True,'verification_mode':'portable numerical parity, not exact regenerated configuration hashes',
            'simulation':simulation_identity(),'checkpoint_rows':64,'generated_configuration_hash_mismatches':hash_mismatches,
            'checkpoint_numeric_differences':differences,'witnesses':witnesses,
            'tolerances':{'checkpoint':{'rtol':1e-12,'atol':1e-10},'configuration':{'rtol':1e-14,'atol':1e-12},
                          'full_ledger':{'rtol':1e-11,'atol':0.002}},
            'exact_checks':['source commit and dependency hashes','retained witness configuration hashes',
                            'dictionary keys and list order','strings, dates, integers, booleans',
                            'no-op restart file hash'],
            'elapsed_seconds':time.time()-started}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'portable_verification_passed':True,'report':str(args.report),'seconds':report['elapsed_seconds']},indent=2))


if __name__=='__main__':
    main()
