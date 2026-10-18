"""Transfer frozen PRIM rules to reserved and local challenge futures."""
import json
import numpy as np
import pandas as pd
from common import ROOT,CORE,LONG
from analyze import features,matches,score,discover

def main():
 models=json.loads((ROOT/'outputs/prim_models.json').read_text());rows=[]
 for phase in ['challenge','boundary','stress','historical']:
  f=ROOT/'outputs'/f'{phase}_normal.csv'
  if not f.exists():continue
  d=pd.read_csv(f);fs=json.loads((ROOT/'inputs'/f'futures_{phase}.json').read_text())
  for h in [str(CORE),str(LONG)]:
   x=features(fs,h)
   for m in models:
    if m['horizon']!=h or not m['boxes']:continue
    g=d[(d.policy==m['policy'])&(d.horizon==h)].set_index('future_id').reindex(x.index)
    if g[m['outcome']].isna().any():raise AssertionError('Incomplete matched set')
    y=(~g[m['outcome']]).to_numpy();union=np.zeros(len(x),bool)
    for b in m['boxes']:
     mask=matches(x,b['rule']);union|=mask
     rows.append(dict(phase=phase,policy=m['policy'],horizon=h,outcome=m['outcome'],box=str(b['box']),**score(y,mask)))
    rows.append(dict(phase=phase,policy=m['policy'],horizon=h,outcome=m['outcome'],box='union',**score(y,union)))
 pd.DataFrame(rows).to_csv(ROOT/'outputs/prim_external_validation.csv',index=False)
 # Peeling sensitivity uses only discovery training data and its old holdout.
 d=pd.read_csv(ROOT/'outputs/main_normal.csv');fs=json.loads((ROOT/'inputs/futures_main.json').read_text());split=json.loads((ROOT/'inputs/discovery_split.json').read_text());x=features(fs,str(CORE));train=x.index.isin(split['train']);sens=[];rules=[]
 for policy in ['reference_100','bps_100','liquidity_cap']:
  for outcome in ['funded','nominal_value']:
   y=(~d[(d.policy==policy)&(d.horizon==str(CORE))].set_index('future_id').reindex(x.index)[outcome]).to_numpy()
   for peel in [.025,.10]:
    m=discover(x.loc[train],y[train],peel=peel);union=np.zeros((~train).sum(),bool)
    for b in m['boxes']:union|=matches(x.loc[~train],b['rule'])
    sens.append(dict(policy=policy,outcome=outcome,peel=peel,boxes=len(m['boxes']),**score(y[~train],union)))
    rules.append(dict(policy=policy,outcome=outcome,peel=peel,boxes=m['boxes']))
 pd.DataFrame(sens).to_csv(ROOT/'outputs/prim_peeling_sensitivity.csv',index=False)
 from common import write_json
 write_json(ROOT/'outputs/prim_peeling_rules.json',rules)

if __name__=='__main__':main()
