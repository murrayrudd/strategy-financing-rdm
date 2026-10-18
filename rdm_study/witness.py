"""Illustrative matched case of financing closure before a principal payment."""
import json,gzip
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import timedelta
from common import ROOT,START,CORE,write_json
from model import run
from metrics import independent_checks
from audit_witnesses import audit

def main():
 f=next(f for f in json.loads((ROOT/'inputs/futures_main.json').read_text()) if f['future_id']=='main_1674')
 retained=pd.read_csv(ROOT/'outputs/all_main.csv');records=[];series={};summaries=[]
 for p in ['liquidity_cap','anticipatory_12']:
  r,paths=run(f,p);independent_checks(r);audit(r)
  expected=set(retained[(retained.future_id==f['future_id'])&(retained.policy==p)].config_sha256)
  assert expected=={r.input_sha256}
  with gzip.open(ROOT/'outputs'/f'witness_{p}.json.gz','wt') as out:json.dump(r.to_dict(),out,allow_nan=False)
  snaps=[r.initial_snapshot]+r.snapshots
  points=pd.DataFrame([dict(date=s['state']['asof'],policy=p,liquid=s['liquid_assets_usd'],reserve_floor=s['reserve_floor_usd'],btc=s['state']['btc'],shares=s['state']['common_shares']) for s in snaps]);points['date']=pd.to_datetime(points.date)
  points=points[points.date<=pd.Timestamp(str(CORE))];series[p]=points;records.append(points)
  core=retained[(retained.future_id==f['future_id'])&(retained.policy==p)&(retained.horizon==str(CORE))].iloc[0]
  summaries.append(dict(policy=p,funded=bool(core.funded),payments=bool(core.payments),common_gross_usd=float(core.common_gross_usd),strc_gross_usd=float(core.strc_gross_usd),common_return=float(core.common_return) if pd.notna(core.common_return) else None,first_stop_date=core.first_stop_date if pd.notna(core.first_stop_date) else None,cash_gap_usd=float(core.cash_gap_usd),permission_gap_usd=float(core.permission_gap_usd)))
 pd.concat(records).to_csv(ROOT/'outputs/witness_cash_series.csv',index=False)
 closed=pd.Series(paths['closed']);inds=closed[closed].index;start=START+timedelta(days=int(inds.min()));end=START+timedelta(days=int(inds.max()))
 write_json(ROOT/'outputs/witness_summary.json',dict(future=f,closure_start=str(start),closure_end=str(end),selection='Illustrative stylized case: cash-cap policy stops on the March 2028 principal date while advance funding meets the five-year funded target. Not used to estimate frequencies.',policies=summaries))
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
 fig,ax=plt.subplots(figsize=(6.7,3.2));ax.axvspan(pd.Timestamp(start),pd.Timestamp(end),color='.9',label='Financing closure')
 for p,color,ls,label in [('liquidity_cap','.45','--','Protect cash only'),('anticipatory_12','black','-','Raise cash in advance')]:
  a=series[p];ax.plot(a.date,a.liquid/1e9,color=color,ls=ls,lw=1.3,label=label)
 a=series['anticipatory_12'];ax.plot(a.date,a.reserve_floor/1e9,color='.5',ls=':',lw=1,label='Required reserve floor')
 stopped=series['liquidity_cap'].iloc[-1]
 ax.scatter([stopped.date],[stopped.liquid/1e9],marker='X',color='.35',s=55,zorder=5)
 ax.annotate('Settlement blocked',xy=(stopped.date,stopped.liquid/1e9),xytext=(pd.Timestamp('2029-06-01'),3.1),fontsize=8,arrowprops={'arrowstyle':'->','color':'.3','lw':.8})
 ax.axvline(pd.Timestamp('2028-03-01'),color='.4',ls=':',lw=.8);ax.set_ylabel('Cash plus Treasuries ($ billion)');ax.legend(frameon=False,fontsize=8,ncol=2,loc='upper right');ax.grid(axis='y',alpha=.2);fig.tight_layout()
 for ext in ['png','svg']:fig.savefig(ROOT/'figures'/('07_cash_timing_witness.'+ext),dpi=250,bbox_inches='tight')
 plt.close(fig);print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
