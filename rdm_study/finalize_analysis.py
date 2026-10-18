"""Assemble complete matched results and explicit-denominator diagnostics."""
import json,hashlib
import numpy as np
import pandas as pd
from common import ROOT,CORE,LONG,write_json
from model import POLICIES
from analyze import summaries,OUTCOMES

def main():
 out=ROOT/'outputs';main=pd.concat([pd.read_csv(out/'main_normal.csv'),pd.read_csv(out/'main_revisions.csv')],ignore_index=True)
 assert len(main)==2000*len(POLICIES)*4
 assert not main.duplicated(['future_id','policy','horizon']).any()
 main.to_csv(out/'all_main.csv',index=False);summaries(main,'all_main')
 for phase,n in [('challenge',512),('historical',26),('boundary',len(json.loads((ROOT/'inputs/futures_boundary.json').read_text()))),('stress',12)]:
  d=pd.read_csv(out/f'{phase}_normal.csv');assert len(d)==n*len(POLICIES)*4
  assert not d.duplicated(['future_id','policy','horizon']).any();summaries(d,phase)
 tail=pd.concat([pd.read_csv(out/'main_tail.csv'),pd.read_csv(out/'revisions_tail.csv')],ignore_index=True)
 assert len(tail)==2000*len(POLICIES)*4
 assert not tail.duplicated(['future_id','policy','variant']).any()
 tail.to_csv(out/'all_tail.csv',index=False);tr=[]
 for (variant,policy),g in tail.groupby(['variant','policy']):
  horizon=str(CORE) if variant.startswith('core') else str(LONG)
  base=main[(main.policy==policy)&(main.horizon==horizon)].set_index('future_id');t=g.set_index('future_id').reindex(base.index)
  assert not (t.funded & ~base.funded).any(),'Historical reserve/payment failure cannot be erased by a tail'
  for criterion in ['payments','funded','nominal_value','bitcoin_per_share']:
   eligible=base[criterion].astype(bool)
   tr.append(dict(variant=variant,policy=policy,criterion=criterion,n=len(t),endpoint_successes=int(eligible.sum()),tail_successes=int(t[criterion].sum()),retained_endpoint_successes=int(t.loc[eligible,criterion].sum()),conditional_retention=float(t.loc[eligible,criterion].mean()) if eligible.any() else None))
 pd.DataFrame(tr).to_csv(out/'tail_retention.csv',index=False)
 futures=pd.DataFrame(json.loads((ROOT/'inputs/futures_main.json').read_text()))
 joined=main.merge(futures[['future_id','authorization_renewal','put_fraction','dependence']],on='future_id',validate='many_to_one')
 groups=[]
 for factor in ['family','authorization_renewal','put_fraction','dependence']:
  a=joined.groupby(['horizon','policy',factor])[OUTCOMES+['payments']].agg(['sum','count','mean']);a.columns=['_'.join(x) for x in a.columns];a=a.reset_index().rename(columns={factor:'group'});a['factor']=factor;groups.append(a)
 pd.concat(groups).to_csv(out/'stratified_performance.csv',index=False)
 # Compare burden and dilution on exactly the same completed, mapped futures.
 economic=[];stop=[]
 for h,g in main.groupby('horizon'):
  domain=g.pivot(index='future_id',columns='policy',values='common_return').dropna().index
  z=g[g.future_id.isin(domain)]
  for p,a in z.groupby('policy'):
   r=dict(horizon=h,policy=p,common_defined_futures=len(domain))
   for col in ['common_return','bitcoin_per_share_change','common_share_growth','bitcoin_sold','annual_preferred_runrate_usd','common_gross_usd','strc_gross_usd','final_bitcoin','daily_common_drawdown']:
    r[col+'_median']=float(a[col].median());r[col+'_q10']=float(a[col].quantile(.1));r[col+'_q90']=float(a[col].quantile(.9))
   economic.append(r)
  for p,a in g.groupby('policy'):
   stop.append(dict(horizon=h,policy=p,n=len(a),payment_stops=int((~a.payments).sum()),reserve_only_failures=int((a.payments&~a.funded).sum()),undefined_mapping=int((~a.mapping_defined).sum()),stops_with_cash_gap=int(((~a.payments)&(a.cash_gap_usd>1e-5)).sum()),stops_with_permission_gap=int(((~a.payments)&(a.permission_gap_usd>1e-5)).sum())))
 pd.DataFrame(economic).to_csv(out/'common_domain_economics.csv',index=False)
 pd.DataFrame(stop).to_csv(out/'failure_decomposition.csv',index=False)
 # Numerical boundary sensitivity is paired, so counts do not hide switching.
 s=pd.read_csv(out/'sensitivity.csv');ss=[]
 for (variant,policy,h),g in s.groupby(['variant','policy','horizon']):
  b=main[(main.policy==policy)&(main.horizon==h)].set_index('future_id').loc[g.future_id];t=g.set_index('future_id').loc[b.index]
  for outcome in OUTCOMES:
   ss.append(dict(variant=variant,policy=policy,horizon=h,outcome=outcome,n=len(g),base_successes=int(b[outcome].sum()),variant_successes=int(t[outcome].sum()),gains=int((t[outcome]&~b[outcome]).sum()),losses=int((~t[outcome]&b[outcome]).sum())))
 pd.DataFrame(ss).to_csv(out/'sensitivity_paired.csv',index=False)
 diagnostic=pd.read_csv(out/'diagnostic_sales.csv');assert len(diagnostic)==8000
 components=pd.concat([main[main.policy.isin(['liquidity_cap','anticipatory_12','anticipatory_sale'])],diagnostic],ignore_index=True)
 summaries(components,'component_diagnostic')
 fresh=pd.read_csv(out/'fresh_component_validation.csv')
 assert len(fresh)==512*4*4 and fresh.transaction_audit_passed.all()
 assert not fresh.duplicated(['future_id','policy','horizon','variant']).any()
 counts={}
 for name in ['main_normal','main_revisions','challenge_normal','historical_normal','boundary_normal','stress_normal','main_tail','revisions_tail','sensitivity','diagnostic_sales','fresh_component_validation']:
  d=pd.read_csv(out/(name+'.csv'));key=['future_id','policy','variant']
  counts[name]=dict(rows=len(d),evaluations=len(d[key].drop_duplicates()),futures=d.future_id.nunique(),policies=d.policy.nunique(),all_prefixes_reconciled=bool(d.ledger_prefixes_reconciled.all()),max_stock_flow_difference=float(d.max_stock_flow_difference.max()),arithmetic_checks=int(d.drop_duplicates(key).independent_checks.sum()))
 write_json(out/'experiment_inventory.json',dict(experiments=counts,total_evaluations=sum(v['evaluations'] for v in counts.values()),all_prefixes_reconciled=all(v['all_prefixes_reconciled'] for v in counts.values())))
 print(json.dumps(counts,indent=2))

if __name__=='__main__':main()
