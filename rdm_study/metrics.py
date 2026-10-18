from collections import defaultdict
from datetime import date
from bisect import bisect_right
import math
import numpy as np
from scipy.special import ndtr
from common import START,CHECKPOINTS,digest
from model import index


def daily_quotes(result,paths):
 """Daily marks with accrual between corporate events; no extra transactions."""
 snaps=[result.initial_snapshot]+result.snapshots
 times=np.array([index(s['state']['asof']) for s in snaps])
 n=times[-1]+1;days=np.arange(n);a=np.searchsorted(times,days,side='right')-1
 def vals(fn):return np.array([fn(s) for s in snaps],float)[a]
 btc=vals(lambda s:s['state']['btc']);shares=vals(lambda s:s['state']['common_shares'])
 cash=vals(lambda s:s['liquid_assets_usd']+s['state']['restricted_cash_usd'])
 claim_usd=vals(lambda s:sum(c['face_native']+c['accrued_native'] for c in s['state']['claims'] if c['currency']=='USD')+s['state']['unallocated_payable_usd'])
 claim_eur=vals(lambda s:sum(c['face_native']+c['accrued_native'] for c in s['state']['claims'] if c['currency']=='EUR'))
 currencies={c['id']:c['currency'] for c in result.configuration['opening']['claims']}
 grouped=defaultdict(lambda:[0.,0.])
 for p in result.configuration['payments']+result.generated_payments:
  if p['kind']=='principal':continue
  key=(currencies[p['claim_id']],p['accrual_start'],p['accrual_end'])
  grouped[key][0]+=p['amount_native'];grouped[key][1]+=p.get('opening_credit_native',0)
 earned={k:np.zeros(n) for k in ['USD','EUR']}
 for (currency,start,end),(amount,credit) in grouped.items():
  s=max(0,(date.fromisoformat(start)-START).days);e=(date.fromisoformat(end)-START).days
  fraction=np.ones(n) if e<=s else np.clip((days-s)/(e-s),0,1)
  earned[currency]+=credit+(amount-credit)*fraction
 claims=claim_usd+earned['USD']-earned['USD'][times[a]]+(claim_eur+earned['EUR']-earned['EUR'][times[a]])*paths['fx'][:n]
 risky=btc*paths['price'][:n];other=cash+result.configuration['initial_point']['net_operating_value_usd']
 strike=claims-other;mode=result.configuration['initial_point']['valuation_mode']
 if mode=='continuation':
  v=.65*math.sqrt(3)
  with np.errstate(divide='ignore',invalid='ignore'):
   d1=(np.log(risky/np.maximum(1e-100,strike))+.5*v*v)/v
  base=np.where(strike<=0,risky-strike,np.maximum(0,risky*ndtr(d1)-strike*ndtr(d1-v)))
 else:base=np.maximum(0,risky-strike)
 quotes=paths['multiple'][:n]*base/shares
 # Exact event snapshots also capture any explicitly supplied closure stress.
 for t,s in zip(times,snaps):quotes[t]=s['conditional_common_price_usd'] if s['quote_defined'] else np.nan
 quotes[quotes<=0]=np.nan
 return quotes


def summarize(result,paths,future,policy,checkpoints=CHECKPOINTS):
 rows=[];snaps=[result.initial_snapshot]+result.snapshots
 daily=daily_quotes(result,paths)
 first=result.initial_snapshot;failure=result.failure or {};paymap={p['id']:p for p in result.configuration['payments']+result.generated_payments}
 points={p['date']:p for p in result.configuration['path']}
 for end in checkpoints:
  if end>result.configuration['path'][-1]['date']:continue
  failed=bool(failure and failure['date']<=end)
  ss=[s for s in snaps if s['state']['asof']<=end];last=ss[-1];state=last['state']
  complete=not failed and last['state']['asof']==end
  reserve=all(s['reserve_compliant'] for s in ss)
  quotes=daily[:index(end)+1];mapping=bool(np.isfinite(quotes).all())
  ret=last['conditional_common_price_usd']/first['conditional_common_price_usd']-1 if complete and mapping else None
  bps=last['btc_per_common_share']/first['btc_per_common_share']-1 if complete else None
  ledger=[e for e in result.ledger if e['date']<=end]
  def total(action,key):return sum(e['details'].get(key,0) for e in ledger if e['action']==action)
  distributions=0.
  for e in ledger:
   if e['action']!='settle_dated_commitments':continue
   for ident in e['details']['payment_ids']:
    pay=paymap[ident]
    if pay['kind']=='dividend':
     currency=next(c['currency'] for c in state['claims'] if c['id']==pay['claim_id'])
     distributions+=pay['amount_native']*points[e['date']]['fx_usd_per_unit'][currency]
  p=points.get(last['state']['asof'],result.configuration['initial_point'])
  pref_run=state['strc_shares']*100*p['strc_annual_rate']
  pref_run+=sum(c['face_native']*{'STRF':.10,'STRE':.10,'STRK':.08,'STRD':.10}.get(c['id'],0)*p['fx_usd_per_unit'][c['currency']] for c in state['claims'])
  funded=complete and reserve;years=(date.fromisoformat(end)-START).days/365.25
  finitequotes=quotes[np.isfinite(quotes)]
  dd=float(np.min(finitequotes/np.maximum.accumulate(finitequotes)-1)) if len(finitequotes) and mapping else None
  rows.append(dict(future_id=future['future_id'],phase=future['phase'],family=future['family'],policy=policy,horizon=end,
   payments=complete,funded=funded,reserve_compliant=reserve,mapping_defined=mapping,
   nominal_value=bool(funded and ret is not None and ret>=-1e-12),annual_5pct=bool(funded and ret is not None and ret>1.05**years-1-1e-12),
   bitcoin_per_share=bool(funded and bps is not None and bps>=-1e-12),common_return=ret,bitcoin_per_share_change=bps,
   first_stop_date=failure.get('date') if failed else None,cash_gap_usd=failure.get('cash_gap_usd',0) if failed else 0,
   permission_gap_usd=max(failure.get('reserve_authorization_gap_usd',0),failure.get('btc_general_use_funding_gap_usd',0)) if failed else 0,
   minimum_reserve_margin_usd=min(s['state']['reserve_designation_usd']-s['reserve_floor_usd'] for s in ss),
   daily_common_drawdown=dd,btc_price_return=float(paths['price'][index(end)]/paths['price'][0]-1),
   common_gross_usd=total('issue_common_atm','gross_usd'),strc_gross_usd=total('issue_strc','gross_usd'),
   bitcoin_sold=-sum(e['balances'].get('btc',0) for e in ledger if e['action']=='sell_bitcoin_for_funding'),
   bitcoin_purchased=sum(e['balances'].get('btc',0) for e in ledger if e['action']=='purchase_bitcoin'),
   preferred_cash_paid_usd=distributions,annual_preferred_runrate_usd=pref_run if complete else None,
   remaining_principal_usd=sum(c['face_native'] for c in state['claims'] if c['kind']=='debt') if complete else None,
   final_bitcoin=state['btc'] if complete else None,final_liquid_usd=last['liquid_assets_usd'] if complete else None,
   common_share_growth=state['common_shares']/first['state']['common_shares']-1 if complete else None,
   config_sha256=result.input_sha256,ledger_entries=len(ledger),ledger_prefixes_reconciled=result.reconciliation['all_prefixes_reconciled']))
 return rows


def independent_checks(result):
 """Stock-flow, authority, payment and entitlement checks at every realized event."""
 previous=result.initial_snapshot['state'];points={p['date']:p for p in result.configuration['path']}
 decisions={d['date']:d for d in result.financing_decisions};issues=[];errors=[];common=0.;strc=0.
 def eq(a,b,label):
  er=abs(a-b);errors.append(er)
  if not math.isclose(a,b,rel_tol=2e-11,abs_tol=.002):raise AssertionError((label,a,b,er))
 for e in result.ledger:
  d=e['details'];after=e['after'];p=points[e['date']]
  if e['action'] in ['issue_common_atm','issue_strc']:
   kind='common' if e['action']=='issue_common_atm' else 'strc'
   qty=d['gross_usd']/d['price_usd'];fee=result.configuration['policy'].get(kind+'_issue_fee_rate',0)
   eq(after['cash_usd']-previous['cash_usd'],d['gross_usd']*(1-fee),'Issue cash')
   eq(after[kind+'_shares']-previous[kind+'_shares'],qty,'Issue shares')
   if kind=='common':common+=d['gross_usd'];issued=common
   else:strc+=d['gross_usd'];issued=strc;issues.append((e['date'],qty))
   if issued>p[kind+'_authorization_gross_limit_usd']+.001:raise AssertionError('Authority exceeded')
   if d['trade_date']>=d['settlement_date']:raise AssertionError('T+1 receipt order invalid')
   holidays=result.configuration['policy'].get('equity_settlement_holidays',[])
   from datetime import timedelta
   t=date.fromisoformat(d['trade_date'])+timedelta(days=1)
   while t.weekday()>=5 or str(t) in holidays:t+=timedelta(days=1)
   if str(t)!=d['settlement_date']:raise AssertionError('Receipt differs from next trading business day')
  if e['action']=='purchase_bitcoin':
   qty=after['btc']-previous['btc'];eq(previous['cash_usd']-after['cash_usd'],qty*p['btc_price_usd']*(1+result.configuration['policy']['btc_purchase_cost_rate']),'BTC purchase')
   buffer=decisions[e['date']].get('liquidity_rule_buffer_usd',p['unreserved_cash_buffer_usd'])
   if after['cash_usd']+after['treasuries_usd']-after['reserve_designation_usd']+.002<buffer:raise AssertionError('Purchase consumed protected cash')
  previous=after
 aggregated=defaultdict(float)
 for p in result.generated_payments:aggregated[p['payment_date']]+=p['amount_native']
 for t in result.configuration['strc_terms']['templates']:
  shares=sum(q for d,q in issues if d<=t['record_date'])
  eq(aggregated[t['payment_date']],shares*100*t['annual_rate']/24,'New STRC entitlement')
 if result.complete and result.pending_placements:raise AssertionError('Unsettled endpoint financing')
 return dict(checks=len(errors),max_absolute_stock_flow_difference=max(errors,default=0),passed=True)
