"""Fresh simulations around a discovered boundary and combined stress cases."""
import json
import numpy as np
from common import ROOT,CORE,write_json
from futures import designs,RANGES
from analyze import features

def main():
 models=json.loads((ROOT/'outputs/prim_models.json').read_text())
 model=next(m for m in models if m['policy']=='bps_100' and m['horizon']==str(CORE) and m['outcome']=='funded')
 fs=json.loads((ROOT/'inputs/futures_main.json').read_text());x=features(fs,str(CORE));byid={f['future_id']:f for f in fs}
 allowed=['bitcoin_cagr','terminal_multiple','strc_base_rate','strc_stress_spread','strc_discount','operating_cashflow_millions','mean_capacity']
 chosen=[]
 for b in model['boxes']:
  for key in allowed:
   if key in b['rule']:
    for side,cut in b['rule'][key].items():chosen.append((key,side,cut))
 if not chosen:chosen=[('bitcoin_cagr','upper',0.)]
 out=[];notes=[]
 for key,side,cut in chosen[:4]:
  near=(x[key]-cut).abs().sort_values().head(16).index
  scale=float(x[key].max()-x[key].min());step=.025*scale
  for ident in near:
   for sign in [-1,1]:
    f=byid[ident].copy();target=cut+sign*step
    if key=='bitcoin_cagr':f['bitcoin_cagr']=(1+f['bitcoin_cagr'])*(1+target)/(1+x.loc[ident,key])-1
    elif key=='terminal_multiple':f['valuation_factor']*=target/x.loc[ident,key]
    elif key=='mean_capacity':f['capacity_scale']*=target/x.loc[ident,key]
    elif key=='operating_cashflow_millions':f['annual_operating_cashflow']=target*1e6
    else:f[key]=target
    mapped={'terminal_multiple':'valuation_factor','mean_capacity':'capacity_scale','operating_cashflow_millions':'annual_operating_cashflow'}.get(key,key)
    lo,hi=RANGES[mapped];f[mapped]=float(np.clip(f[mapped],lo,hi))
    f.update(future_id=f'boundary_{len(out):04d}',phase='boundary',boundary_parent=ident,boundary_feature=key,boundary_cut=cut,boundary_side=sign)
    out.append(f)
  notes.append(dict(feature=key,side=side,cut=cut,step=step))
 write_json(ROOT/'inputs/futures_boundary.json',out)
 write_json(ROOT/'inputs/boundary_design.json',dict(target='bps_100 funded 2031-06-30',boundaries=notes,n=len(out),interpretation='Local perturbations of observed profiles, not independent evidence or a probability sample.'))
 stress=[]
 for growth in [-.25,0.,.25]:
  for put in [0.,1.]:
   for renewal in [False,True]:
    f=designs(1,11900+len(stress),'stress')[0]
    f.update(future_id=f'stress_{len(stress):02d}',bitcoin_cagr=growth,put_fraction=put,authorization_renewal=renewal,shock_depth=.8,shock_start=1.1,recovery_years=3.,closure_months=36.,closure_threshold=.2,capacity_scale=.05,strc_base_rate=.16,strc_stress_spread=.06,strc_discount=15.,annual_operating_cashflow=-300e6,eur_terminal_factor=1.35,valuation_factor=.35,valuation_stress_strength=1.2,dependence='linked',generator='plateau',repeated_shock=True)
    stress.append(f)
 write_json(ROOT/'inputs/futures_stress.json',stress)
 print('Boundary',len(out),'compound stress',len(stress))

if __name__=='__main__':main()
