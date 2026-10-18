"""Matched structural and policy sensitivities, selected before challenge results."""
import json,time,argparse
from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
import pandas as pd
from common import ROOT,LONG,write_json
from model import configuration,POLICIES
import engine
from metrics import summarize,independent_checks
from execution import run_batch
from pathlib import Path

def variants():
 primary=['reference_100','bps_100','liquidity_cap','anticipatory_12','anticipatory_sale']
 specs=[]
 for p in primary:
  for floor in [1e-6,1.]:specs.append(dict(label=f'execution_floor_{floor:g}',policy=p,kwargs={'execution_floor':floor}))
  specs.append(dict(label='face_valuation',policy=p,kwargs={'valuation_mode':'face'}))
  specs.append(dict(label='market_value_capacity_2pct',policy=p,patch={'common_market_cap_fraction':.02,'strc_market_cap_fraction':.02}))
 for p in POLICIES:specs.append(dict(label='half_puts',policy=p,future_patch={'put_fraction':.5}))
 for months in [6,18]:specs.append(dict(label=f'cash_coverage_{months}',policy='liquidity_cap',patch={'liquidity_lookahead_months':months}))
 for cap in [.25,1.]:specs.append(dict(label=f'preferred_cap_{cap:g}',policy='liquidity_cap',patch={'strc_new_principal_cap_fraction':cap}))
 return specs

def worker(f):
 rows=[]
 for v in variants():
  ff=dict(f,**v.get('future_patch',{}));cfg,paths=configuration(ff,v['policy'],**v.get('kwargs',{}))
  cfg['policy'].update(v.get('patch',{}));cfg['metadata']['rdm_sensitivity']=v['label']
  r=engine.run_dated_configuration(cfg,ff['future_id']+'_'+v['label']+'_'+v['policy']);audit=independent_checks(r)
  rr=summarize(r,paths,ff,v['policy'])
  for row in rr:row.update(variant=v['label'],independent_checks=audit['checks'],max_stock_flow_difference=audit['max_absolute_stock_flow_difference'])
  rows.extend(rr)
 return dict(future_id=f['future_id'],rows=rows)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=8);ap.add_argument('--output-dir',type=Path,default=ROOT/'outputs');ap.add_argument('--tag',default='sensitivity');a=ap.parse_args()
 fs=json.loads((ROOT/'inputs/futures_main.json').read_text());rng=np.random.default_rng(72119)
 selected=sorted(rng.choice(len(fs),size=256,replace=False));fs=[fs[i] for i in selected]
 settings=dict(seed=72119,variants=variants(),policies=POLICIES)
 d=run_batch(fs,settings,worker,lambda f:f,directory=a.output_dir,tag=a.tag,workers=a.workers)
 summary=d.groupby(['variant','policy','horizon'])[['funded','nominal_value','bitcoin_per_share']].agg(['sum','mean','count'])
 summary.columns=['_'.join(x) for x in summary.columns];summary.to_csv(a.output_dir/(a.tag+'_performance.csv'))

if __name__=='__main__':main()
