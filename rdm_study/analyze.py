"""RDM performance, held-out PRIM scenario discovery and paired tradeoffs."""
import json,argparse,warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier,export_text
from sklearn.metrics import balanced_accuracy_score
from common import ROOT,START,CORE,LONG,write_json
from futures import external_paths
from model import index

from labels import LABELS
OUTCOMES=['funded','nominal_value','annual_5pct','bitcoin_per_share']

def features(futures,horizon):
 rows=[];end=index(horizon)
 for f in futures:
  p=external_paths(f);sl=slice(0,end+1);cap=p['capacity'][sl]
  rows.append(dict(future_id=f['future_id'],bitcoin_cagr=(p['price'][end]/p['price'][0])**(365.25/end)-1,
   bitcoin_min_ratio=float(p['price'][sl].min()/p['price'][0]),bitcoin_max_drawdown=float(p['drawdown'][sl].max()),
   terminal_multiple=float(p['multiple'][end]),minimum_multiple=float(p['multiple'][sl].min()),
   mean_capacity=float(cap.mean()),closed_months=float(p['closed'][sl].sum()/30.4375),
   strc_base_rate=f['strc_base_rate'],strc_stress_spread=f['strc_stress_spread'],strc_discount=f['strc_discount'],
   operating_cashflow_millions=f['annual_operating_cashflow']/1e6,eur_terminal_factor=float(p['fx'][end]/p['fx'][0]),
   put_fraction=float(f['put_fraction']),authorization_renewal=int(f['authorization_renewal'])))
 return pd.DataFrame(rows).set_index('future_id')

def matches(x,rule):
 mask=np.ones(len(x),bool)
 for k,b in rule.items():
  if 'lower' in b:mask &= x[k].to_numpy()>=b['lower']
  if 'upper' in b:mask &= x[k].to_numpy()<=b['upper']
 return mask

def score(y,mask):
 y=np.asarray(y,bool);mask=np.asarray(mask,bool)
 return dict(n=len(y),failures=int(y.sum()),inside=int(mask.sum()),inside_failures=int((y&mask).sum()),
  density=float(y[mask].mean()) if mask.any() else None,coverage=float((y&mask).sum()/y.sum()) if y.any() else None,
  mass=float(mask.mean()),false_positive_count=int((~y&mask).sum()))

def discover(x,y,peel=.05):
 from ema_workbench.analysis import prim
 if np.all(y) or not np.any(y):return dict(constant_target=bool(y[0]),boxes=[],reason='No target variation')
 search=prim.Prim(x.reset_index(drop=True),np.asarray(y,bool),peel_alpha=peel,paste_alpha=peel,mass_min=.05)
 boxes=[];trajectories=[]
 for n in range(3):
  b=search.find_box()
  if b is None:break
  tr=b.peeling_trajectory.copy();tr['box']=n+1
  candidates=tr[(tr.res_dim<=4)&(tr.res_dim>0)]
  if candidates.empty:break
  preferred=candidates[candidates.density>=.9]
  if len(preferred):sel=int(preferred.sort_values(['coverage','res_dim','density'],ascending=[False,True,False]).index[0])
  else:sel=int(candidates.sort_values(['density','coverage','res_dim'],ascending=[False,False,True]).index[0])
  if tr.loc[sel,'density']<=np.mean(y)+.025:break
  b.select(sel);lim=b.box_lims[sel];rule={}
  for k in x:
   z={}
   if lim.loc[0,k]>search.box_init.loc[0,k]:z['lower']=float(lim.loc[0,k])
   if lim.loc[1,k]<search.box_init.loc[1,k]:z['upper']=float(lim.loc[1,k])
   if z:rule[k]=z
  boxes.append(dict(box=n+1,rule=rule,trajectory_index=sel,density_target_met=bool(tr.loc[sel,'density']>=.9),training=score(y,matches(x,rule))))
  trajectories.extend(tr.assign(selected=tr.index==sel).to_dict('records'))
  if len(boxes)==3:break
 return dict(boxes=boxes,trajectories=trajectories)

def summaries(d,tag):
 agg=d.groupby(['horizon','policy'])[OUTCOMES+['payments','mapping_defined']].agg(['sum','mean','count'])
 agg.columns=['_'.join(c) for c in agg.columns];agg.reset_index().to_csv(ROOT/'outputs'/f'{tag}_performance.csv',index=False)
 pairs=[]
 for h,g in d.groupby('horizon'):
  for outcome in OUTCOMES:
   p=g.pivot(index='future_id',columns='policy',values=outcome)
   for a in p:
    for b in p:
     if a==b:continue
     both=p[[a,b]].dropna().astype(bool)
     pairs.append(dict(horizon=h,outcome=outcome,policy=a,comparator=b,n=len(both),gains=int((both[a]&~both[b]).sum()),losses=int((~both[a]&both[b]).sum()),both_success=int((both[a]&both[b]).sum())))
 pd.DataFrame(pairs).to_csv(ROOT/'outputs'/f'{tag}_paired.csv',index=False)
 # Regret has a common, explicitly restricted domain, with failures tabulated above.
 regret=[]
 for h,g in d.groupby('horizon'):
  p=g.pivot(index='future_id',columns='policy',values='common_return').dropna()
  if len(p):
   r=p.max(axis=1).to_numpy()[:,None]-p
   for pol in p:
    regret.append(dict(horizon=h,policy=pol,common_defined_futures=len(p),median_return=float(p[pol].median()),return_q10=float(p[pol].quantile(.1)),regret_q90=float(r[pol].quantile(.9)),max_regret=float(r[pol].max())))
 pd.DataFrame(regret).to_csv(ROOT/'outputs'/f'{tag}_conditional_regret.csv',index=False)
 return agg

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--phase',default='main');ap.add_argument('--discovery',action='store_true');a=ap.parse_args()
 d=pd.read_csv(ROOT/'outputs'/f'{a.phase}_normal.csv');summaries(d,a.phase)
 if not a.discovery:return
 futures=json.loads((ROOT/'inputs'/f'futures_{a.phase}.json').read_text())
 ids=[f['future_id'] for f in futures];rng=np.random.default_rng(6601);perm=rng.permutation(ids)
 train=set(perm[:int(.75*len(ids))]);test=set(ids)-train
 write_json(ROOT/'inputs/discovery_split.json',dict(seed=6601,train=sorted(train),holdout=sorted(test),note='Internal design holdout; not an independent probability sample.'))
 allmodels=[];alltrajectories=[];tests=[];trees=[]
 for horizon in [str(CORE),str(LONG)]:
  x=features(futures,horizon);x.to_csv(ROOT/'outputs'/f'exogenous_features_{horizon}.csv')
  istrain=x.index.isin(train);g=d[d.horizon==horizon]
  for policy in sorted(g.policy.unique()):
   target=g[g.policy==policy].set_index('future_id').reindex(x.index)
   for outcome in ['funded','nominal_value','bitcoin_per_share']:
    y=(~target[outcome]).to_numpy();model=discover(x.loc[istrain],y[istrain])
    meta=dict(policy=policy,horizon=horizon,outcome=outcome)
    trajectory=model.pop('trajectories',[])
    alltrajectories.extend([dict(**r,**meta) for r in trajectory])
    for split,mask in [('train',istrain),('holdout',~istrain)]:
     union=np.zeros(mask.sum(),bool)
     for box in model['boxes']:
      boxmask=matches(x.loc[mask],box['rule']);union|=boxmask
      tests.append(dict(**meta,split=split,box=str(box['box']),**score(y[mask],boxmask)))
     if model['boxes']:tests.append(dict(**meta,split=split,box='union',**score(y[mask],union)))
    allmodels.append(dict(**meta,**model))
    if len(set(y[istrain]))==2:
     tree=DecisionTreeClassifier(max_depth=3,min_samples_leaf=50,random_state=6601).fit(x.loc[istrain],y[istrain])
     pred=tree.predict(x.loc[~istrain]);varied=len(set(y[~istrain]))==2
     trees.append(dict(**meta,balanced_accuracy=float(balanced_accuracy_score(y[~istrain],pred)) if varied else None,holdout_failures=int(y[~istrain].sum()),holdout_nonfailures=int((~y[~istrain]).sum()),interpretation='Both outcome classes represented' if varied else 'Holdout has one class; balanced accuracy is not informative',rules=export_text(tree,feature_names=list(x.columns),decimals=3)))
    print('Discovery',horizon,policy,outcome,len(model['boxes']),flush=True)
 write_json(ROOT/'outputs/prim_models.json',allmodels)
 pd.DataFrame(tests).to_csv(ROOT/'outputs/prim_validation.csv',index=False)
 pd.DataFrame(alltrajectories).to_csv(ROOT/'outputs/prim_trajectories.csv',index=False)
 write_json(ROOT/'outputs/tree_diagnostics.json',trees)

if __name__=='__main__':main()
