"""Frozen fresh-future test of cash timing and Bitcoin sale authority."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd
from common import ROOT, CORE, LONG, digest, write_json
from execution import run_batch, simulation_identity
from futures import designs
from model import POLICIES, configuration
from metrics import summarize, independent_checks
from audit_witnesses import audit
from analyze import summaries
import engine

N = 512
SEED = 271107
POLICY_ORDER = ['liquidity_cap', 'sales_only', 'anticipatory_12', 'anticipatory_sale']
INPUT = ROOT/'inputs/futures_component_validation.json'
LOCK = ROOT/'evidence/component_validation_lock.json'


def policy_definitions():
    result = {p: deepcopy(POLICIES[p]) for p in POLICY_ORDER if p != 'sales_only'}
    result['sales_only'] = dict(result['liquidity_cap'], general_sale_authority=result['anticipatory_sale']['general_sale_authority'])
    return result


def freeze():
    if INPUT.exists() or LOCK.exists():
        raise RuntimeError('Fresh validation design already exists; it will not be regenerated.')
    futures = designs(N, SEED, 'challenge')
    for i, f in enumerate(futures):
        f.update(future_id=f'component_validation_{i:04d}', phase='component_validation')
    write_json(INPUT, futures)
    write_json(LOCK, dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(), n=N, seed=SEED,
        input_sha256=hashlib.sha256(INPUT.read_bytes()).hexdigest(), policies=policy_definitions(),
        simulation=simulation_identity(), primary_horizon=str(CORE), secondary_horizon=str(LONG),
        primary_outcomes=['payments', 'funded'], secondary_outcomes=['nominal_value', 'bitcoin_per_share'],
        comparisons=[['sales_only','liquidity_cap'], ['anticipatory_12','liquidity_cap'],
                     ['anticipatory_sale','sales_only'], ['anticipatory_sale','anticipatory_12']],
        interpretation='Compare matched gains and losses for both levers, including their interaction. No policy or threshold retuning.',
        hypotheses=['Adding sale permission improves payment completion more than funded success.',
                    'Adding advance funding improves funded success more than payment completion.'],
        scope='Fresh random draws from the reserved challenge design: 256 historical-block paths from 2020–2025 and 256 plateau-recovery paths. Not a new model structure or an untouched historical data pool.'))
    print('Frozen fresh component validation:', N, 'futures', flush=True)


def check_lock():
    lock = json.loads(LOCK.read_text())
    if hashlib.sha256(INPUT.read_bytes()).hexdigest() != lock['input_sha256']:
        raise RuntimeError('Frozen fresh-validation inputs changed.')
    if policy_definitions() != lock['policies'] or simulation_identity() != lock['simulation']:
        raise RuntimeError('Frozen fresh-validation policies, code, source, or environment changed.')
    return lock


def worker(future):
    rows = []
    for policy in POLICY_ORDER:
        base = 'liquidity_cap' if policy == 'sales_only' else policy
        cfg, paths = configuration(future, base)
        if policy == 'sales_only':
            authority = policy_definitions()[policy]['general_sale_authority']
            for point in cfg['path']:
                point['btc_general_use_gross_limit_usd'] = authority
            cfg['policy']['name'] = policy
            cfg['metadata']['rdm_policy'] = policy_definitions()[policy]
        result = engine.run_dated_configuration(cfg, future['future_id']+'_'+policy)
        checks = independent_checks(result)
        witness = audit(result)
        for row in summarize(result, paths, future, policy):
            row.update(variant='fresh_component_validation', independent_checks=checks['checks'],
                       max_stock_flow_difference=checks['max_absolute_stock_flow_difference'],
                       transaction_audit_passed=witness['passed'])
            rows.append(row)
    return dict(future_id=future['future_id'], rows=rows)


def analyze(data, directory):
    # summaries writes into the study output directory; additional primary
    # effects below are always written beside the evaluated batch.
    if Path(directory).resolve() == (ROOT/'outputs').resolve():
        summaries(data, 'fresh_component_validation')
    effects = []
    for horizon, group in data.groupby('horizon'):
        for outcome in ['payments', 'funded', 'nominal_value', 'bitcoin_per_share']:
            wide = group.pivot(index='future_id', columns='policy', values=outcome).astype(bool)
            for new, old in json.loads(LOCK.read_text())['comparisons']:
                effects.append(dict(horizon=horizon, outcome=outcome, policy=new, comparator=old,
                    n=len(wide), base_successes=int(wide[old].sum()), variant_successes=int(wide[new].sum()),
                    gains=int((wide[new] & ~wide[old]).sum()), losses=int((~wide[new] & wide[old]).sum()),
                    net_gain=int(wide[new].sum()-wide[old].sum())))
    pd.DataFrame(effects).to_csv(Path(directory)/'fresh_component_effects.csv', index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'outputs')
    args = parser.parse_args()
    if args.freeze:
        freeze()
        return
    lock = check_lock()
    futures = json.loads(INPUT.read_text())
    data = run_batch(futures, dict(validation_lock_sha256=digest(lock)), worker, lambda f: f,
                     directory=args.output_dir, tag='fresh_component_validation', workers=args.workers)
    if len(data) != N*4*4 or not data.transaction_audit_passed.all():
        raise RuntimeError('Fresh component validation is incomplete or failed its transaction audit.')
    analyze(data, args.output_dir)


if __name__ == '__main__':
    main()
