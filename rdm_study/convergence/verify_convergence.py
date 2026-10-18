"""Check complete sampling, accounting, and scenario-discovery evidence."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse, itertools, json
import numpy as np
import pandas as pd
from common import ROOT, write_json
from model import POLICIES
from futures import RANGES
from component_validation import policy_definitions
from analyze import matches, score
from run_convergence import HERE, check_lock, sha

def main():
    if not __debug__:raise RuntimeError('Verification requires assertions enabled.')
    p=argparse.ArgumentParser();p.add_argument('--largest',type=int,choices=[5000,10000],required=True);a=p.parse_args()
    lock=check_lock();policies=dict(POLICIES);policies['sales_only']=policy_definitions()['sales_only']
    assert policies==lock['policies']
    sizes=[n for n in [2000,5000,10000] if n<=a.largest]
    stage=json.loads((HERE/'outputs'/f'stage_{a.largest}_summary.json').read_text())
    if a.largest==10000:
        prior=json.loads((HERE/'outputs/stage_5000_summary.json').read_text())
        assert prior['extend_to_10000']
    else:assert not stage['extend_to_10000']
    ids=set();records=[]
    for b in lock['batches']:
        if b['n'] not in sizes:continue
        tag=b['tag'];n=b['n'];fs=json.loads((HERE/'inputs'/f'{tag}.json').read_text())
        f=pd.DataFrame(fs)
        assert len(f)==n and f.future_id.is_unique and not ids.intersection(f.future_id)
        ids.update(f.future_id)
        assert sum(f.family=='block')==n//4
        assert sum(f.put_fraction)==sum(f.authorization_renewal)==sum(f.dependence=='linked')==n//2
        for variable,(low,high) in RANGES.items():
            strata=np.floor((f[variable].to_numpy()-low)/(high-low)*n).astype(int)
            assert np.array_equal(np.sort(strata),np.arange(n)),(tag,variable)
        split=json.loads((HERE/'inputs'/f'{tag}_split.json').read_text())
        assert len(split['train'])==3*n//4 and len(split['holdout'])==n//4
        assert not set(split['train'])&set(split['holdout'])
        assert set(split['train'])|set(split['holdout'])==set(f.future_id)
        d=pd.read_csv(HERE/'outputs'/f'{tag}.csv',float_precision='round_trip')
        assert len(d)==44*n and not d.duplicated(['future_id','policy','horizon']).any()
        assert set(d.policy)==set(policies) and set(d.future_id)==set(f.future_id)
        assert (d.groupby(['policy','horizon']).size()==n).all()
        assert d.ledger_prefixes_reconciled.all() and (d.independent_checks>0).all()
        assert (~d.funded|d.payments).all()
        assert all((~d[o]|d.funded).all() for o in ['nominal_value','annual_5pct','bitcoin_per_share'])
        perf=pd.read_csv(HERE/'outputs'/f'{tag}_performance.csv')
        for r in perf.itertuples():
            z=d[(d.policy==r.policy)&(d.horizon==r.horizon)][r.outcome]
            assert r.successes==int(z.sum()) and abs(r.share-z.mean())<1e-12
        pair=pd.read_csv(HERE/'outputs'/f'{tag}_paired.csv')
        for (h,o),g in pair.groupby(['horizon','outcome']):
            w=d[d.horizon==h].pivot(index='future_id',columns='policy',values=o).astype(bool)
            for r in g.itertuples():
                gains=int((w[r.policy]&~w[r.comparator]).sum());losses=int((~w[r.policy]&w[r.comparator]).sum())
                assert gains==r.gains and losses==r.losses and abs(r.net_share-(gains-losses)/n)<1e-12
        models=json.loads((HERE/'outputs'/f'{tag}_prim.json').read_text())
        assert models['input_sha256']==sha(HERE/'outputs'/f'{tag}.csv')
        assert models['analysis_sha256']==sha(HERE/'analyze_convergence.py')
        assert len(models['results'])==12
        for m in models['results']:
            x=pd.read_csv(HERE/'outputs'/f"{tag}_features_{m['horizon']}.csv",index_col='future_id')
            x=x.loc[split['holdout']]
            y=~d[(d.policy==m['policy'])&(d.horizon==m['horizon'])].set_index('future_id').reindex(x.index)[m['outcome']].astype(bool).to_numpy()
            for kind in ['first','union']:
                boxes=m['model']['boxes'][:1] if kind=='first' else m['model']['boxes']
                mask=np.zeros(len(x),bool)
                for box in boxes:mask|=matches(x,box['rule'])
                actual=score(y,mask);record=next(s for s in m['scores'] if s['split']=='holdout' and s['kind']==kind)
                assert all(record[k]==v for k,v in actual.items())
        records.append(dict(tag=tag,futures=n,policy_evaluations=n*11,checkpoint_rows=len(d),
            independent_checks=int(d.drop_duplicates(['future_id','policy']).independent_checks.sum()),
            max_stock_flow_difference=float(d.max_stock_flow_difference.max()),
            csv_sha256=sha(HERE/'outputs'/f'{tag}.csv'),passed=True))
    assert len(records)==3*len(sizes) and len(ids)==sum(r['futures'] for r in records)
    assert stage['evaluations']==sum(r['policy_evaluations'] for r in records)
    result=dict(passed=True,largest_n=a.largest,batches=records,unique_futures=len(ids),
                evaluations=stage['evaluations'],protocol_sha256=sha(HERE/'design_lock.json'),
                checks=['unchanged engine, source and numerical environment','policy definitions match prospective lock',
                'exact continuous LHS strata and category margins','disjoint future IDs and training/holdout partitions',
                'complete policy and checkpoint cross products','all ledger prefixes and independent stock-flow checks',
                'nested outcome definitions','independently recomputed performance and paired counts',
                'recomputed fresh-holdout PRIM classification scores','prespecified escalation followed'])
    write_json(HERE/'verification.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='batches'},indent=2))

if __name__=='__main__':main()
