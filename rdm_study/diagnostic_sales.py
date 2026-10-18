"""Post-discovery component ablation: sales permission without advance funding.

This diagnostic does not retune any primary policy or PRIM rule and makes no
claim of reserved-set validation. It isolates an identified attribution risk.
"""
import json,time,argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import pandas as pd
from common import ROOT,write_json
from model import configuration
import engine
from metrics import summarize,independent_checks
from execution import run_batch
from model import POLICIES
from pathlib import Path

def worker(f):
 c,paths=configuration(f,'liquidity_cap')
 for p in c['path']:p['btc_general_use_gross_limit_usd']=6753703000.
 c['policy']['name']='sales_only';c['metadata']['rdm_policy']=dict(c['metadata']['rdm_policy'],general_sale_authority=6753703000.)
 c['metadata']['diagnostic']='Same protected cash and preferred cap; general sales permission added; advance common funding disabled.'
 r=engine.run_dated_configuration(c,f['future_id']+'_sales_only');audit=independent_checks(r)
 rows=summarize(r,paths,f,'sales_only')
 for row in rows:row.update(variant='component_diagnostic',independent_checks=audit['checks'],max_stock_flow_difference=audit['max_absolute_stock_flow_difference'])
 return dict(future_id=f['future_id'],rows=rows)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=4);ap.add_argument('--output-dir',type=Path,default=ROOT/'outputs');ap.add_argument('--tag',default='diagnostic_sales');a=ap.parse_args()
 fs=json.loads((ROOT/'inputs/futures_main.json').read_text())
 settings=dict(base_policy=POLICIES['liquidity_cap'],general_sale_authority=6753703000.,anticipatory=False)
 run_batch(fs,settings,worker,lambda f:f,directory=a.output_dir,tag=a.tag,workers=a.workers)

if __name__=='__main__':main()
