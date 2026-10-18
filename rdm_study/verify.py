"""Meaningful engine, source-replay, information-set and schedule checks."""
import sys,gzip,json,math,time
from copy import deepcopy
from datetime import date,timedelta
import numpy as np
import pandas as pd
from common import *
from terms import *
from model import *
from metrics import independent_checks,daily_quotes
from treasury_company.market_io import run_configuration as legacy_run


def state_close(a,b):
 if isinstance(a,dict):
  assert set(a)==set(b)
  for k in a:state_close(a[k],b[k])
 elif isinstance(a,list):
  assert len(a)==len(b)
  for x,y in zip(a,b):state_close(x,y)
 elif isinstance(a,(float,int)) and not isinstance(a,bool):
  assert math.isclose(a,b,rel_tol=1e-11,abs_tol=.003),(a,b)
 else:assert a==b,(a,b)


def main():
 t0=time.time();records=[]
 sys.path.insert(0,str(REPO/'inverse'));import study
 jobs=json.loads((REPO/'inverse/inputs/jobs.json').read_text())
 retained=pd.read_csv(REPO/'inverse/results/scenario_evaluations.csv')
 expected=retained[retained.kind=='strc'].set_index('job_id').result_sha256.to_dict()
 # Full original engine replays and economic-state parity after optimization.
 selected=[]
 for screen in ['reference','adaptive']:
  for regime in ['open','capacity','drawdown_closure']:
   candidates=[j for j in jobs if j['kind']=='strc' and j['policy']==screen and j['regime']==regime and j['future_strc_rate']==.12 and j['strc_scale'] in [0.,1.]]
   selected.extend(candidates[:2])
 for j in selected:
  with gzip.open(REPO/'inverse/inputs'/(j['template']+'.json.gz'),'rt') as f:base=json.load(f)
  c,_=study.configuration(base,j,0.)
  original=legacy_run(c);raw=deepcopy(c);ident=raw.pop('configuration_id')
  assert digest(original.to_dict())==expected[j['job_id']],'Frozen result replay hash differs'
  optimized=engine.run_dated_configuration(raw,ident)
  assert original.complete==optimized.complete
  state_close(original.failure,optimized.failure)
  state_close(original.initial_snapshot,optimized.initial_snapshot)
  state_close(original.snapshots,optimized.snapshots)
  independent_checks(optimized)
  records.append(dict(check='original economic replay',job_id=j['job_id'],passed=True,result_sha256=digest(original.to_dict())))
 fs=json.loads((ROOT/'inputs/futures_main.json').read_text())
 for branch in [0.,.5,1.]:
  f=deepcopy(fs[1]);f.update(put_fraction=branch,strc_base_rate=.10,strc_stress_spread=0,authorization_renewal=True)
  c,paths=configuration(f,'liquidity_cap',end=TAIL)
  p=c['payments'];debts={x['id']:x for x in c['opening']['claims'] if x['kind']=='debt'}
  for ident,claim in debts.items():
   pp=[x for x in p if x['claim_id']==ident and x['kind']=='principal']
   assert len(pp)==1 and math.isclose(pp[0]['amount_native'],claim['face_native'])
   assert all(x['payment_date']<=pp[0]['payment_date'] for x in p if x['claim_id']==ident and x['kind']=='interest')
  for t,u in zip(c['strc_terms']['templates'],c['strc_terms']['templates'][1:]):
   assert t['accrual_end']==u['record_date']
   assert u['annual_rate']>=t['annual_rate']-.0025-1e-12
   if date.fromisoformat(u['record_date']).day!=15:assert u['annual_rate']==t['annual_rate']
  r=engine.run_dated_configuration(c,'fixture')
  audit=independent_checks(r)
  records.append(dict(check='extended schedule and stock flow',put_fraction=branch,**audit))
  # Daily valuation agrees with exact event states. Source formula checked
  # independently on one intervening-day hand reconstruction below.
  q=daily_quotes(r,paths)
  for s in r.snapshots:
   if s['quote_defined']:assert math.isclose(q[index(s['date'])],s['conditional_common_price_usd'],rel_tol=1e-12)
 # Month boundary, leap-day and currency calendar facts.
 fed,market,euro=calendars()
 assert date(2027,6,18) not in fed and date(2027,6,18) in market
 assert following(date(2028,12,31),fed)==date(2029,1,2)
 assert following(date(2029,3,31),euro)>following(date(2029,3,31),fed)
 assert date(2028,2,29) in list(boundaries(date(2028,3,1)))
 records.append(dict(check='leap year and multiple business calendars',passed=True))
 # Changes after the core checkpoint cannot alter any preceding state/action.
 f=deepcopy(fs[3]);f.update(authorization_renewal=True,bitcoin_cagr=.2,shock_depth=.3,strc_discount=0.)
 base,paths=run(f,'liquidity_cap',end=LONG)
 closure,cp=run(f,'liquidity_cap',end=LONG,closure_at=CORE,closure_stress=True)
 aa=[s for s in base.snapshots if s['date']<=str(CORE)]
 bb=[s for s in closure.snapshots if s['date']<=str(CORE)]
 state_close(aa,bb)
 records.append(dict(check='no look ahead across financing price and rate closure',passed=True,states_checked=len(aa)))
 # Disturb all future rate and market inputs only after a chosen date.
 c,paths=configuration(f,'liquidity_12',end=LONG);d=deepcopy(c);cut='2028-06-30'
 for p in d['path']:
  if p['date']>cut:p['btc_price_usd']*=.6;p['multiple']*=.5;p['capacity_multiplier']=0
 r1=engine.run_dated_configuration(c,'before');r2=engine.run_dated_configuration(d,'after')
 state_close([s for s in r1.snapshots if s['date']<=cut],[s for s in r2.snapshots if s['date']<=cut])
 records.append(dict(check='future market perturbation prefix invariance',passed=True))
 # Horizon extension preserves identical prefixes when the exogenous path is fixed.
 short,_=run(f,'liquidity_12',end=CORE)
 state_close(short.snapshots,[s for s in r1.snapshots if s['date']<=str(CORE)])
 records.append(dict(check='same-future horizon prefix invariance',passed=True))
 # Future holder elections are not manager knowledge before their notice window.
 f0=deepcopy(f);f1=deepcopy(f);f0['put_fraction']=0.;f1['put_fraction']=1.
 z0,_=run(f0,'liquidity_12');z1,_=run(f1,'liquidity_12')
 cut='2027-08-20'
 state_close([s for s in z0.snapshots if s['date']<=cut],[s for s in z1.snapshots if s['date']<=cut])
 records.append(dict(check='unknown future put election prefix invariance',passed=True))
 # Independently reconstruct non-event daily marks from the source accrual
 # and valuation functions, rather than relying on event-value overwrites.
 from dataclasses import replace
 from treasury_company.dated import earned,Payment,Claim
 snaps=[r1.initial_snapshot]+r1.snapshots
 q=daily_quotes(r1,paths);payments=[Payment(**p) for p in r1.configuration['payments']+r1.generated_payments]
 eventdates={s['state']['asof'] for s in snaps};checked=0
 for k in range(5,len(q),37):
  dt=START+timedelta(days=k)
  if str(dt) in eventdates:continue
  anchor=max((s for s in snaps if s['state']['asof']<str(dt)),key=lambda s:s['state']['asof'])
  raw=deepcopy(anchor['state']);raw['claims']=[Claim(**c) for c in raw['claims']];s=engine.Opening(**raw)
  for claim in s.claims:
   claim.accrued_native+=sum(earned(p,str(dt),str(START),claim)-earned(p,anchor['state']['asof'],str(START),claim) for p in payments if p.claim_id==claim.id)
  point=engine.Point(**dict(c['initial_point'],date=str(dt),btc_price_usd=float(paths['price'][k]),multiple=float(paths['multiple'][k]),fx_usd_per_unit={'USD':1.,'EUR':float(paths['fx'][k])}))
  mark=engine.mark(s,point)['conditional_common_price_usd']
  assert math.isclose(q[k],mark,rel_tol=1e-10,abs_tol=1e-8),(dt,q[k],mark)
  checked+=1
 records.append(dict(check='independent intervening day accrual and valuation',passed=True,days_checked=checked))
 # Independently hand-count the longest coupon-bearing instrument.
 for branch,count,total in [(1.,6,54e6),(0.,12,108e6)]:
  fx=deepcopy(f);fx['put_fraction']=branch
  cfg,_=configuration(fx,'bps_100',end=TAIL)
  coupons=[p for p in cfg['payments'] if p['claim_id']=='2032' and p['kind']=='interest']
  assert len(coupons)==count and math.isclose(sum(p['amount_native'] for p in coupons),total)
 records.append(dict(check='2032 instrument independently counted cash coupons',passed=True))
 # Exhausting inventory must not create a negative Bitcoin asset by one ULP.
 rr,_=run(fs[20],'reference_100')
 assert min(s['state']['btc'] for s in rr.snapshots)>=0
 records.append(dict(check='Bitcoin inventory exhaustion regression',passed=True))
 # Re-run the revised-policy information checks instead of relying on a
 # previously saved verification record.
 revisions=[]
 for policy in ['anticipatory_12','anticipatory_sale']:
  long,paths=run(f,policy,end=LONG)
  short,_=run(f,policy,end=CORE)
  state_close(short.snapshots,[s for s in long.snapshots if s['date']<=str(CORE)])
  closed,_=run(f,policy,end=LONG,closure_at=CORE,closure_stress=True)
  state_close([s for s in long.snapshots if s['date']<=str(CORE)], [s for s in closed.snapshots if s['date']<=str(CORE)])
  cfg,_=configuration(f,policy);changed=deepcopy(cfg);cut='2028-06-30'
  for point in changed['path']:
   if point['date']>cut:point['btc_price_usd']*=.6;point['multiple']*=.5;point['capacity_multiplier']=0
  altered=engine.run_dated_configuration(changed,'future_market_change')
  state_close([s for s in long.snapshots if s['date']<=cut],[s for s in altered.snapshots if s['date']<=cut])
  z0,_=run(f0,policy);z1,_=run(f1,policy);cut='2027-08-20'
  state_close([s for s in z0.snapshots if s['date']<=cut],[s for s in z1.snapshots if s['date']<=cut])
  for result in [long,short,closed,altered,z0,z1]:independent_checks(result)
  revisions.append(dict(policy=policy,no_lookahead_and_horizon_prefix=True,stock_flow_and_entitlements=True))
  records.append(dict(check='revised policy information and horizon invariance',policy=policy,passed=True))
 write_json(ROOT/'outputs/revision_verification.json',revisions)
 write_json(ROOT/'outputs/verification.json',dict(passed=True,checks=records,elapsed_seconds=time.time()-t0))
 print(json.dumps(dict(passed=True,records=len(records),seconds=time.time()-t0),indent=2))

if __name__=='__main__':main()
