"""Compile long futures into the auditable corporate event and settlement ledger."""
from copy import deepcopy
from datetime import date,timedelta
from calendar import monthrange
from bisect import bisect_right
import numpy as np
from common import *
from terms import schedule,calendars,following,preceding,DEBT,PREF_RATES
from futures import external_paths
import engine

POLICIES={}
for screen in ['reference','bps']:
 for scale in [0.,.5,1.]:
  POLICIES[f'{screen}_{int(scale*100)}']=dict(screen=screen,strc_scale=scale,liquidity_months=0,preferred_cap=None,anticipatory=False,general_sale_authority=0.)
POLICIES['liquidity_12']=dict(screen='bps',strc_scale=1.,liquidity_months=12,preferred_cap=None,anticipatory=False,general_sale_authority=0.)
POLICIES['liquidity_cap']=dict(screen='bps',strc_scale=1.,liquidity_months=12,preferred_cap=.5,anticipatory=False,general_sale_authority=0.)
if (ROOT/'inputs/revised_policies.json').exists():
 POLICIES.update(json.loads((ROOT/'inputs/revised_policies.json').read_text()))


def index(d):return max(0,(date.fromisoformat(d) if isinstance(d,str) else d).__sub__(START).days)


def configuration(future,policy_id,end=LONG,closure_at=None,closure_stress=False,valuation_mode=None,execution_floor=.01):
 base=source_base();rule=POLICIES[policy_id];paths=external_paths(future,base['initial_point'])
 def stress(d):return float(paths['stress'][min(index(d),len(paths['stress'])-1)])
 opening,payments,terms,possible=schedule(base,future,end,stress)
 if closure_at and closure_stress:
  z=np.clip((np.arange(len(paths['price']))-index(closure_at))/365.25,0,1)
  paths['price']=paths['price']*np.exp(np.log(.60)*z)
  paths['multiple']=paths['multiple']*np.exp(np.log(.75)*z)
  rate_effective=min(date.fromisoformat(t['record_date']) for t in terms['templates'] if date.fromisoformat(t['record_date']).day==15 and date.fromisoformat(t['record_date'])>closure_at+timedelta(days=20))
  changed={}
  for t in terms['templates']:
   if date.fromisoformat(t['record_date'])>=rate_effective:
    t['annual_rate']+=.04;changed[t['id']]=t['annual_rate']
  for pay in payments:
   if pay['id'] in changed:
    pay['amount_native']=opening['strc_shares']*100*changed[pay['id']]/24
 fed,market,euro=calendars()
 # Preserve the source's initial program calendar; extend with at most one
 # eligible regular STRC delivery date per month, each targeting $400 million.
 programs={date.fromisoformat(p['date']) for p in base['path'] if p['strc_issue_target_gross_usd']}
 for y in range(2027,end.year+1):
  for m in range(1,13):
   e=date(y,m,monthrange(y,m)[1]);mid=date(y,m,15)
   if e<=date(2027,9,30) or e>end:continue
   eligible=[d for d in [mid,e] if d.weekday()<5 and d not in market]
   if eligible:programs.add(max(eligible))
 programs={d for d in programs if START<d<=end}
 opdates={date(y,m,monthrange(y,m)[1]) for y in range(2026,end.year+1) for m in range(1,13) if START<date(y,m,monthrange(y,m)[1])<=end}
 rawdates={date.fromisoformat(p['payment_date']) for p in payments if START<date.fromisoformat(p['payment_date'])<=end}|programs|opdates|{end}|{date.fromisoformat(x) for x in CHECKPOINTS if START<date.fromisoformat(x)<=end}
 roles={d:dict() for d in rawdates}
 # One-day advance placement for known commitments. No issuance occurs at a
 # weekend corporate cash event; earlier placements deliver on a business day.
 for d in sorted(rawdates):
  delivery=d if d.weekday()<5 and d not in market else following(preceding(d,market),market)
  if delivery.weekday()>=5 or delivery in market:raise AssertionError('Invalid delivery')
  trade=preceding(delivery,market)
  if trade<=START:continue
  r=roles.setdefault(trade,{})
  r['financing_for_date']=max(r.get('financing_for_date',str(d)),str(d))
  r['common_capacity']=True
  roles.setdefault(delivery,{})['receipt']=True
  if d in programs:
   if delivery!=d:raise AssertionError('Preferred delivery must be an eligible record')
   r['program']=True;r['scheduled_strc_settlement_date']=str(delivery)
 # All trade dates now have their explicit T+1 receipt.
 for d,r in list(roles.items()):
  if r.get('common_capacity') or r.get('program'):
   receive=following(d+timedelta(days=1),market)
   if receive>end:continue
   roles.setdefault(receive,{})['receipt']=True
 active_ends=[t['accrual_end'] for t in terms['templates']]
 points=[]
 for d in sorted(roles):
  if d<=START:continue
  r=roles[d];i=index(d);t=terms['templates'][bisect_right(active_ends,str(d-timedelta(days=1)))]
  p=base['initial_point'].copy();p['date']=str(d)
  k=(d.year-START.year-int((d.month,d.day)<(START.month,START.day))) if future['authorization_renewal'] else 0
  auth=6e9*(1+k)
  cap=float(paths['capacity'][i]);price=float(paths['price'][i]);mult=float(paths['multiple'][i]);execution=float(paths['execution'][i]);rate=t['annual_rate']
  if closure_at and d>closure_at:
   cap=0
  p.update(btc_price_usd=price,multiple=mult,fx_usd_per_unit={'USD':1.,'EUR':float(paths['fx'][i])},
           capacity_multiplier=cap,strc_execution_price_usd=execution,strc_annual_rate=rate,
           operating_cashflow_usd=future['annual_operating_cashflow']/12 if d in opdates else 0.,
           allow_general_use_of_reserve=True,common_program_target_gross_usd=.4e9 if r.get('program') else 0.,
           strc_issue_target_gross_usd=.4e9*rule['strc_scale'] if r.get('program') else 0.,
           common_issue_cap_gross_usd=1.1e9 if r.get('common_capacity') else 0.,
           strc_issue_cap_gross_usd=.4e9*rule['strc_scale'] if r.get('program') else 0.,
           common_authorization_gross_limit_usd=auth,strc_authorization_gross_limit_usd=auth*rule['strc_scale'],
           btc_general_use_gross_limit_usd=rule['general_sale_authority'],
           equity_trading_open=d.weekday()<5 and d not in market,
           btc_purchase_cap=100000. if r.get('receipt') else 0.)
  if r.get('financing_for_date'):p['financing_for_date']=r['financing_for_date']
  if r.get('program'):p['scheduled_strc_settlement_date']=r['scheduled_strc_settlement_date']
  if valuation_mode:p['valuation_mode']=valuation_mode
  points.append(p)
 initial=deepcopy(base['initial_point']);initial['allow_general_use_of_reserve']=True
 if valuation_mode:initial['valuation_mode']=valuation_mode
 if valuation_mode=='face':
  state=engine.Opening(**dict(opening,claims=[engine.Claim(**c) for c in opening['claims']]))
  original_quote=engine.mark(state,engine.Point(**base['initial_point']))['conditional_common_price_usd']
  face_quote=engine.mark(state,engine.Point(**initial))['conditional_common_price_usd']
  adjustment=original_quote/face_quote
  initial['multiple']*=adjustment
  for p in points:p['multiple']*=adjustment
  paths['multiple']=paths['multiple']*adjustment
 policy=deepcopy(base['policy'])
 policy.update(name=policy_id,common_min_execution_price_usd=execution_floor,equity_settlement_lag_business_days=1,equity_settlement_holidays=sorted(str(x) for x in market),
               common_growth_objective='nav' if rule['screen']=='reference' else 'bitcoin',
               liquidity_lookahead_months=rule['liquidity_months'],strc_new_principal_cap_fraction=rule['preferred_cap'],
               anticipatory_common_financing=rule['anticipatory'])
 cfg=dict(engine_version='0.6.0',opening=opening,payments=payments,initial_point=initial,path=points,policy=policy,
          criteria=dict(require_reserve_compliance=True,min_terminal_equity_return=0),strc_terms=terms,
          metadata=dict(rdm_future=future,rdm_policy=rule,rdm_horizon=str(end),rdm_closure_at=str(closure_at) if closure_at else None,
                        rdm_annual_operating_cashflow_usd=future['annual_operating_cashflow'],rdm_possible_retirement_dates=possible,
                        source_template=TEMPLATE,information_cutoff='2026-08-03',
                        limitations=['No automatic conversion, preferred deferral, restructuring or new debt.','Future holiday calendars project recurring rules.','Fixed original secured-loan and opening reconciliation approximations retained.','Common execution floor is an analyst stress boundary, not an asserted exchange rule.']))
 return cfg,paths


def run(future,policy_id,end=LONG,**kwargs):
 cfg,paths=configuration(future,policy_id,end=end,**kwargs)
 return engine.run_dated_configuration(cfg,future['future_id']+'_'+policy_id+'_'+str(end)),paths
