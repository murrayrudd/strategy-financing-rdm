"""Recreate one full ledger and check its retained configuration hash."""
import argparse,json,gzip
from datetime import date
import pandas as pd
from common import ROOT,CORE,LONG,TAIL,write_json
from model import run
from metrics import summarize,independent_checks

def main():
 p=argparse.ArgumentParser();p.add_argument('future_id');p.add_argument('policy');p.add_argument('--phase',default='main');p.add_argument('--variant',default='normal',choices=['normal','core_closure','long_closure','core_stress_closure','long_stress_closure']);p.add_argument('--out',required=True);a=p.parse_args()
 f=next(f for f in json.loads((ROOT/'inputs'/f'futures_{a.phase}.json').read_text()) if f['future_id']==a.future_id)
 core=a.variant.startswith('core');closure=(CORE if core else LONG) if a.variant!='normal' else None
 end=(date(2032,6,30) if core else TAIL) if closure else LONG
 r,paths=run(f,a.policy,end=end,closure_at=closure,closure_stress='stress' in a.variant)
 independent_checks(r)
 records=[]
 for name in [f'{a.phase}_normal.csv','main_revisions.csv','main_tail.csv','revisions_tail.csv']:
  file=ROOT/'outputs'/name
  if file.exists():
   d=pd.read_csv(file);records.extend(d[(d.future_id==a.future_id)&(d.policy==a.policy)&(d.variant==a.variant)].config_sha256.tolist())
 if records and set(records)!={r.input_sha256}:raise AssertionError('Configuration differs from retained record')
 obj=r.to_dict();obj['rdm_independent_checks']=independent_checks(r)
 with gzip.open(a.out,'wt') as out:json.dump(obj,out,allow_nan=False)
 print(json.dumps(dict(input_sha256=r.input_sha256,complete=r.complete,failure=r.failure,out=a.out,retained_config_matched=bool(records)),indent=2))

if __name__=='__main__':main()
