"""Prespecified policy and scenario-discovery convergence diagnostics."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse, itertools, json, warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import pandas as pd
from common import ROOT, CORE, LONG, write_json
from analyze import features, discover, matches, score
from run_convergence import HERE, check_lock, sha, PAIRS, PRIM_POLICIES

TARGETS=['payments','funded','nominal_value','annual_5pct','bitcoin_per_share']

def union_mask(x,boxes):
    mask=np.zeros(len(x),bool)
    for box in boxes:mask|=matches(x,box['rule'])
    return mask

def prim_job(task):
    tag,policy,horizon,outcome=task
    x=pd.read_csv(HERE/'outputs'/f'{tag}_features_{horizon}.csv',index_col='future_id')
    d=pd.read_csv(HERE/'outputs'/f'{tag}.csv')
    y=~d[(d.policy==policy)&(d.horizon==horizon)].set_index('future_id').reindex(x.index)[outcome].astype(bool).to_numpy()
    split=json.loads((HERE/'inputs'/f'{tag}_split.json').read_text());train=x.index.isin(split['train'])
    probe=pd.read_csv(ROOT/'outputs'/f'exogenous_features_{horizon}.csv',index_col='future_id')
    old=pd.read_csv(ROOT/'outputs/all_main.csv')
    yp=~old[(old.policy==policy)&(old.horizon==horizon)].set_index('future_id').reindex(probe.index)[outcome].astype(bool).to_numpy()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');model=discover(x.loc[train],y[train])
    meta=dict(tag=tag,policy=policy,horizon=horizon,outcome=outcome)
    scores=[]
    for label,xx,yy in [('train',x.loc[train],y[train]),('holdout',x.loc[~train],y[~train]),('common_probe',probe,yp)]:
        for kind,boxes in [('first',model['boxes'][:1]),('union',model['boxes'])]:
            scores.append(dict(**meta,split=label,kind=kind,**score(yy,union_mask(xx,boxes))))
    # The old rule is never reselected using fresh outcomes.
    frozen=json.loads((ROOT/'outputs/prim_models.json').read_text())
    old_model=next(m for m in frozen if m['policy']==policy and m['horizon']==horizon and m['outcome']==outcome)
    for kind,boxes in [('first',old_model['boxes'][:1]),('union',old_model['boxes'])]:
        scores.append(dict(**meta,split='frozen_rule_fresh_holdout',kind=kind,
                           **score(y[~train],union_mask(x.loc[~train],boxes))))
    return dict(**meta,model=model,scores=scores)

def analyze_batch(batch,workers):
    tag=batch['tag'];n=batch['n'];directory=HERE/'outputs'
    d=pd.read_csv(directory/f'{tag}.csv')
    if len(d)!=n*11*4 or d.duplicated(['future_id','policy','horizon']).any() or not d.ledger_prefixes_reconciled.all():
        raise RuntimeError('Incomplete or invalid batch '+tag)
    rows=[];paired=[];tails=[]
    for h,g in d.groupby('horizon'):
        for p,z in g.groupby('policy'):
            for o in TARGETS:
                rows.append(dict(tag=tag,n=n,replicate=batch['replicate'],horizon=h,policy=p,outcome=o,successes=int(z[o].sum()),share=float(z[o].mean())))
            defined=z.common_return.dropna()
            tails.append(dict(tag=tag,n=n,horizon=h,policy=p,defined_returns=len(defined),
                              common_return_q10=float(defined.quantile(.1)) if len(defined) else None,
                              common_return_median=float(defined.median()) if len(defined) else None))
        for o in TARGETS:
            w=g.pivot(index='future_id',columns='policy',values=o).astype(bool)
            for new,old in PAIRS:
                gains=int((w[new]&~w[old]).sum());losses=int((~w[new]&w[old]).sum())
                paired.append(dict(tag=tag,n=n,replicate=batch['replicate'],horizon=h,outcome=o,policy=new,comparator=old,gains=gains,losses=losses,net_share=(gains-losses)/n))
    pd.DataFrame(rows).to_csv(directory/f'{tag}_performance.csv',index=False)
    pd.DataFrame(paired).to_csv(directory/f'{tag}_paired.csv',index=False)
    pd.DataFrame(tails).to_csv(directory/f'{tag}_conditional_returns.csv',index=False)
    futures=json.loads((HERE/'inputs'/f'{tag}.json').read_text())
    for h in [str(CORE),str(LONG)]:features(futures,h).to_csv(directory/f'{tag}_features_{h}.csv')
    output=directory/f'{tag}_prim.json'
    if output.exists():
        retained=json.loads(output.read_text())
        if retained['input_sha256']!=sha(directory/f'{tag}.csv') or retained['analysis_sha256']!=sha(__file__):
            raise RuntimeError('Existing discovery results have a different input or analysis.')
        return
    tasks=list(itertools.product([tag],PRIM_POLICIES,[str(CORE),str(LONG)],['funded','nominal_value']))
    results=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        jobs={pool.submit(prim_job,t):t for t in tasks}
        for job in as_completed(jobs):
            results.append(job.result());print('PRIM',*jobs[job],flush=True)
    results.sort(key=lambda r:(r['policy'],r['horizon'],r['outcome']))
    write_json(output,dict(input_sha256=sha(directory/f'{tag}.csv'),analysis_sha256=sha(__file__),results=results))
    pd.DataFrame([s for r in results for s in r['scores']]).to_csv(directory/f'{tag}_prim_scores.csv',index=False)

def jaccard(a,b):
    if isinstance(a,set):return len(a&b)/len(a|b) if a|b else 1.
    return float((a&b).sum()/(a|b).sum()) if (a|b).any() else 1.

def evaluate(sizes):
    lock=check_lock();batches=[b for b in lock['batches'] if b['n'] in sizes]
    directory=HERE/'outputs';largest=max(sizes);previous=max(s for s in sizes if s<largest)
    performance=pd.concat([pd.read_csv(directory/f"{b['tag']}_performance.csv") for b in batches])
    paired=pd.concat([pd.read_csv(directory/f"{b['tag']}_paired.csv") for b in batches])
    scores=pd.concat([pd.read_csv(directory/f"{b['tag']}_prim_scores.csv") for b in batches])
    criteria=[]
    def add(domain,name,value,limit,passed,**meta):
        criteria.append(dict(domain=domain,criterion=name,value=float(value),limit=float(limit),passed=bool(passed),**meta))
    for (h,p),g in performance[(performance.outcome=='funded')&performance.horizon.isin(lock['horizons'])].groupby(['horizon','policy']):
        high=g[g.n==largest].share;low=g[g.n==previous].share
        spread=100*(high.max()-high.min());shift=100*abs(high.mean()-low.mean())
        add('policy','replicate_range_pp',spread,2.,spread<=2.+1e-9,horizon=h,policy=p)
        add('policy','mean_shift_pp',shift,1.,shift<=1.+1e-9,horizon=h,policy=p)
    for (h,p,c),g in paired[(paired.outcome=='funded')&paired.horizon.isin(lock['horizons'])].groupby(['horizon','policy','comparator']):
        high=g[g.n==largest].net_share;low=g[g.n==previous].net_share
        spread=100*(high.max()-high.min());shift=100*abs(high.mean()-low.mean())
        add('paired','replicate_range_pp',spread,2.,spread<=2.+1e-9,horizon=h,policy=p,comparator=c)
        add('paired','mean_shift_pp',shift,1.,shift<=1.+1e-9,horizon=h,policy=p,comparator=c)
    interpretations=[]
    for (tag,h),g in paired[paired.horizon.isin(lock['horizons'])].groupby(['tag','horizon']):
        def effect(p,c,o):return float(g[(g.policy==p)&(g.comparator==c)&(g.outcome==o)].iloc[0].net_share)
        flags=dict(advance_no_sales=effect('anticipatory_12','liquidity_cap','funded')>0,
            advance_with_sales=effect('anticipatory_sale','sales_only','funded')>0,
            sales_payment_effect_larger=effect('sales_only','liquidity_cap','payments')>effect('sales_only','liquidity_cap','funded'),
            advance_reserve_effect_larger=effect('anticipatory_sale','sales_only','funded')>effect('anticipatory_sale','sales_only','payments'))
        interpretations.append(dict(tag=tag,horizon=h,**flags,passed=all(flags.values())))
    primary=scores[(scores.policy=='bps_100')&(scores.horizon==str(CORE))&(scores.split=='common_probe')].copy()
    size_map={b['tag']:b['n'] for b in batches};primary['size']=primary.tag.map(size_map)
    for (o,k),g in primary.groupby(['outcome','kind']):
        for metric in ['density','coverage']:
            high=g[g['size']==largest][metric];low=g[g['size']==previous][metric]
            spread=100*(high.max()-high.min());shift=100*abs(high.mean()-low.mean())
            add('prim',metric+'_range_pp',spread,10.,high.notna().all() and spread<=10.+1e-9,outcome=o,kind=k)
            add('prim',metric+'_mean_shift_pp',shift,10.,high.notna().all() and shift<=10.+1e-9,outcome=o,kind=k)
    overlaps=[];feature_rows=[]
    for size in sizes:
        selected=[b for b in batches if b['n']==size]
        models={b['tag']:json.loads((directory/f"{b['tag']}_prim.json").read_text())['results'] for b in selected}
        for p,h,o in itertools.product(PRIM_POLICIES,lock['horizons'],['funded','nominal_value']):
            probe=pd.read_csv(ROOT/'outputs'/f'exogenous_features_{h}.csv',index_col='future_id')
            fitted={t:next(m['model'] for m in rr if m['policy']==p and m['horizon']==h and m['outcome']==o) for t,rr in models.items()}
            for ta,tb in itertools.combinations(fitted,2):
                for kind in ['first','union']:
                    ba=fitted[ta]['boxes'][:1] if kind=='first' else fitted[ta]['boxes']
                    bb=fitted[tb]['boxes'][:1] if kind=='first' else fitted[tb]['boxes']
                    value=jaccard(union_mask(probe,ba),union_mask(probe,bb))
                    overlaps.append(dict(n=size,policy=p,horizon=h,outcome=o,kind=kind,a=ta,b=tb,mask_jaccard=value))
                    if size==largest and p=='bps_100' and h==str(CORE):
                        add('prim','mask_jaccard',value,.6,bool(ba and bb) and value>=.6,outcome=o,kind=kind,a=ta,b=tb)
                ba=fitted[ta]['boxes'][:1];bb=fitted[tb]['boxes'][:1]
                fa={(v,d) for box in ba for v,bounds in box['rule'].items() for d in bounds}
                fb={(v,d) for box in bb for v,bounds in box['rule'].items() for d in bounds}
                value=jaccard(fa,fb)
                if size==largest and p=='bps_100' and h==str(CORE):
                    add('prim','feature_direction_jaccard',value,.5,bool(ba and bb) and value>=.5,outcome=o,a=ta,b=tb)
            for tag,m in fitted.items():
                for box in m['boxes']:
                    for variable,bounds in box['rule'].items():
                        for direction,cutoff in bounds.items():
                            feature_rows.append(dict(n=size,tag=tag,policy=p,horizon=h,outcome=o,box=box['box'],variable=variable,direction=direction,cutoff=cutoff,
                                probe_percentile=float((probe[variable]<=cutoff).mean())))
    frame=pd.DataFrame(criteria)
    flags={domain:bool(g.passed.all()) for domain,g in frame.groupby('domain')}
    flags['interpretation']=all(i['passed'] for i in interpretations)
    result=dict(largest_n=largest,previous_n=previous,batches=len(batches),futures=sum(b['n'] for b in batches),
                evaluations=sum(b['n'] for b in batches)*11,criteria=flags,all_primary_passed=all(flags.values()),
                extend_to_10000=largest<10000 and not all(flags.values()),
                failed_checks=frame[~frame.passed].to_dict('records'),interpretations=interpretations,
                protocol_sha256=sha(HERE/'design_lock.json'),
                input_and_result_sha256={str(p.relative_to(HERE)):sha(p) for b in batches for p in [HERE/'inputs'/f"{b['tag']}.json",directory/f"{b['tag']}.csv",directory/f"{b['tag']}_prim.json"]})
    for name,data in [('performance',performance),('paired',paired),('prim_scores',scores),('criteria',frame),('prim_overlap',pd.DataFrame(overlaps)),('prim_thresholds',pd.DataFrame(feature_rows))]:
        data.to_csv(directory/f'stage_{largest}_{name}.csv',index=False)
    write_json(directory/f'stage_{largest}_summary.json',result)
    print(json.dumps({k:result[k] for k in ['largest_n','futures','evaluations','criteria','all_primary_passed','extend_to_10000']},indent=2),flush=True)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sizes',nargs='+',type=int,default=[2000,5000]);ap.add_argument('--tag');ap.add_argument('--workers',type=int,default=8);ap.add_argument('--evaluate-only',action='store_true');a=ap.parse_args()
    lock=check_lock()
    if not a.evaluate_only:
        for b in lock['batches']:
            if (a.tag and b['tag']==a.tag) or (not a.tag and b['n'] in a.sizes):analyze_batch(b,a.workers)
    if not a.tag:evaluate(a.sizes)

if __name__=='__main__':main()
