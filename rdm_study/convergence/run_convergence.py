"""Prospectively locked LHS replication study using the unchanged 1.1 engine."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse, hashlib, json, importlib.metadata
from datetime import datetime, timezone
import numpy as np
from common import ROOT, CORE, LONG, digest, write_json
from execution import run_batch, simulation_identity
from futures import designs
from model import POLICIES
from run_study import worker as ordinary_worker
from diagnostic_sales import worker as sales_worker
from component_validation import policy_definitions

HERE = Path(__file__).resolve().parent
LOCK = HERE/'design_lock.json'
SEEDS = {2000: [410011, 410029, 410047], 5000: [510013, 510031, 510047],
         10000: [610031, 610043, 610051]}
PAIRS = [['anticipatory_12','bps_100'], ['anticipatory_sale','bps_100'],
         ['sales_only','liquidity_cap'], ['anticipatory_12','liquidity_cap'],
         ['anticipatory_sale','sales_only'], ['anticipatory_sale','anticipatory_12']]
PRIM_POLICIES = ['reference_100', 'bps_100', 'liquidity_cap']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def identity():
    return dict(simulation=simulation_identity(),
                supplemental_code={n:sha(HERE/n) for n in ['run_convergence.py','analyze_convergence.py']},
                discovery_code_sha256=sha(ROOT/'analyze.py'),
                discovery_dependencies={n:importlib.metadata.version(n) for n in ['ema_workbench','scikit-learn']})

def freeze():
    if LOCK.exists(): raise RuntimeError('The convergence protocol is already frozen.')
    batches=[]
    for n, seeds in SEEDS.items():
        for replicate, seed in enumerate(seeds, 1):
            tag=f'lhs_{n}_r{replicate}'
            futures=designs(n,seed,'main')
            for i,f in enumerate(futures):
                f.update(future_id=f'{tag}_{i:05d}',phase=tag)
            path=HERE/'inputs'/f'{tag}.json'
            write_json(path,futures)
            split=np.random.default_rng(seed+700000).permutation([f['future_id'] for f in futures]).tolist()
            split_path=HERE/'inputs'/f'{tag}_split.json'
            write_json(split_path,dict(train=sorted(split[:3*n//4]),holdout=sorted(split[3*n//4:])))
            batches.append(dict(tag=tag,n=n,replicate=replicate,seed=seed,
                                input_sha256=sha(path),split_sha256=sha(split_path)))
    policies=dict(POLICIES);policies['sales_only']=policy_definitions()['sales_only']
    protocol=dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),identity=identity(),batches=batches,
        policies=policies,pairs=PAIRS,prim_policies=PRIM_POLICIES,
        horizons=[str(CORE),str(LONG)],primary_outcomes=['payments','funded'],
        secondary_outcomes=['nominal_value','annual_5pct','bitcoin_per_share'],
        original_main_sha256=sha(ROOT/'inputs/futures_main.json'),
        original_prim_sha256=sha(ROOT/'outputs/prim_models.json'),
        sampling='Independent ordinary scrambled Latin hypercubes, 15 continuous inputs and 3 binary branches. Same main design mixture and generators; no nested prefixes or appended LHS claim.',
        discovery='Unchanged PRIM algorithm and selection, 75/25 split by future. Fit three report reference policies for funded and nominal-value failure at both long endpoints. No policy retuning.',
        common_probe='The original 2000 main futures, excluded from every new fit. Used only to compare selected regions; fresh per-batch holdouts provide separate validation.',
        criteria=dict(policy_share_range_pp=2.0,policy_mean_shift_pp=1.0,
            paired_effect_range_pp=2.0,paired_effect_mean_shift_pp=1.0,
            policy_scope='Funded shares for all 11 policies at both long horizons; six prespecified funded paired net effects at both horizons. Payments and shareholder targets are secondary.',
            substantive='Advance funding increases funded success in both sale settings; adding sales improves payment completion more than funded success; adding advance funding with sales improves funded success more than payment completion, at both long horizons in every replicate.',
            prim_density_coverage_range_pp=10.0,prim_mask_jaccard_min=0.60,
            prim_feature_direction_jaccard_min=0.50,
            prim_scope='BPS 100 first box and union for funded and nominal-value failure at June 2031, compared across all three largest-size fits on the common probe. First-box feature/direction overlap is also required. Other policies and 2033 are secondary.',
            prim_mean_shift_pp=10.0,
            interpretation='Pragmatic prespecified tolerances for this study, not universal statistical thresholds. Three replications cannot certify exhaustive coverage.'),
        escalation='After 2000 and 5000 batches, run all three predesignated 10000 batches if any primary policy, component interpretation, or PRIM criterion fails. Stop after 10000 regardless; report any remaining instability rather than retuning.',
        boundaries='No new closure-tail, structural or historical-pool experiment. Conditional sample frequencies are not event probabilities. Near-equal rankings and rare-event thresholds require separate interpretation.')
    write_json(LOCK,protocol)
    print(json.dumps({'frozen':str(LOCK),'batches':len(batches),'identity':digest(protocol['identity'])}),flush=True)

def check_lock():
    lock=json.loads(LOCK.read_text())
    if lock['identity']!=identity(): raise RuntimeError('Frozen convergence code, source, or environment changed.')
    if sha(ROOT/'inputs/futures_main.json')!=lock['original_main_sha256'] or sha(ROOT/'outputs/prim_models.json')!=lock['original_prim_sha256']:
        raise RuntimeError('Original retained evidence changed.')
    for b in lock['batches']:
        if sha(HERE/'inputs'/f"{b['tag']}.json")!=b['input_sha256'] or sha(HERE/'inputs'/f"{b['tag']}_split.json")!=b['split_sha256']:
            raise RuntimeError('Frozen convergence inputs or splits changed.')
    return lock

def worker(f):
    a=ordinary_worker((f,list(POLICIES),'normal'))
    a['rows'].extend(sales_worker(f)['rows'])
    for row in a['rows']:row['variant']='sampling_convergence'
    return a

def run_one(batch,workers):
    lock=check_lock();tag=batch['tag']
    fs=json.loads((HERE/'inputs'/f'{tag}.json').read_text())
    d=run_batch(fs,dict(protocol_sha256=digest(lock),batch=batch),worker,lambda f:f,
                directory=HERE/'outputs',tag=tag,workers=workers)
    if len(d)!=batch['n']*11*4 or not d.ledger_prefixes_reconciled.all():
        raise RuntimeError('Incomplete or unreconciled convergence batch.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--sizes',nargs='+',type=int,default=[2000,5000]);p.add_argument('--workers',type=int,default=8);p.add_argument('--tag');a=p.parse_args()
    if a.freeze:return freeze()
    lock=check_lock()
    for b in lock['batches']:
        if (a.tag and b['tag']==a.tag) or (not a.tag and b['n'] in a.sizes):run_one(b,a.workers)

if __name__=='__main__':main()
