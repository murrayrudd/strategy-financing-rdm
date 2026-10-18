"""Matched-future experiment with streaming, resumable result checkpoints."""
import argparse,json,time,os
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from datetime import date
import pandas as pd
from common import ROOT,LONG,CORE,TAIL,write_json
from model import POLICIES,run
from metrics import summarize,independent_checks
from execution import run_batch


def worker(task):
 f,policies,mode=task;rows=[];audits=[]
 for policy in policies:
  if mode=='normal':variants=[('normal',LONG,None,False)]
  elif mode=='tail':variants=[('core_closure',date(2032,6,30),CORE,False),('long_closure',TAIL,LONG,False),('core_stress_closure',date(2032,6,30),CORE,True),('long_stress_closure',TAIL,LONG,True)]
  else:raise ValueError(mode)
  for label,end,closure,stress in variants:
   result,paths=run(f,policy,end=end,closure_at=closure,closure_stress=stress)
   checks=independent_checks(result)
   audits.append(checks)
   rr=summarize(result,paths,f,policy,checkpoints=[str(end)] if mode=='tail' else None) if mode=='tail' else summarize(result,paths,f,policy)
   for r in rr:r['variant']=label;r['independent_checks']=checks['checks'];r['max_stock_flow_difference']=checks['max_absolute_stock_flow_difference']
   rows.extend(rr)
 return dict(future_id=f['future_id'],rows=rows,audits=audits)


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--phase',default='main');ap.add_argument('--workers',type=int,default=8);ap.add_argument('--limit',type=int);ap.add_argument('--offset',type=int,default=0);ap.add_argument('--mode',default='normal',choices=['normal','tail']);ap.add_argument('--policies',nargs='+');ap.add_argument('--tag');ap.add_argument('--output-dir',type=Path,default=ROOT/'outputs');a=ap.parse_args()
 futures=json.loads((ROOT/'inputs'/('futures_'+a.phase+'.json')).read_text())[a.offset:]
 if a.limit:futures=futures[:a.limit]
 policies=a.policies or list(POLICIES)
 tag=a.tag or a.phase+'_'+a.mode
 for p in policies:
  if p not in POLICIES:raise ValueError(f'Unknown policy: {p}')
 settings=dict(phase=a.phase,mode=a.mode,policies={p:POLICIES[p] for p in policies},offset=a.offset,limit=a.limit)
 run_batch(futures,settings,worker,lambda f:(f,policies,a.mode),directory=a.output_dir,tag=tag,workers=a.workers)

if __name__=='__main__':main()
