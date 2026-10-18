"""Source-checked contractual dates and conditional cash-payment schedules.

Conditional scope: existing instruments retained, no conversion/redemption,
cash declaration of all preferred distributions until the first failed payment.
Calendar rules are projected under current recurring holiday rules; exceptional
future closures are not claimed known. Market issuance uses a conservative union
of Fed and exchange holidays. The secured-loan approximation remains labeled.
"""
from calendar import monthrange
from datetime import date,timedelta
from functools import lru_cache
from copy import deepcopy
import holidays
from dateutil.easter import easter
from common import START,TAIL

DEBT={
 '2028':dict(rate=.00625,months=[3,9],day=15,put='2027-09-15',maturity='2028-09-15'),
 '2029':dict(rate=0,months=[6,12],day=1,put='2028-06-01',maturity='2029-12-01'),
 '2030A':dict(rate=.00625,months=[3,9],day=15,put='2028-09-15',maturity='2030-03-15'),
 '2030B':dict(rate=0,months=[3,9],day=1,put='2028-03-01',maturity='2030-03-01'),
 '2031':dict(rate=.00875,months=[3,9],day=15,put='2028-09-15',maturity='2031-03-15'),
 '2032':dict(rate=.0225,months=[6,12],day=15,put='2029-06-15',maturity='2032-06-15')}
PREF_RATES={'STRF':.10,'STRE':.10,'STRK':.08,'STRD':.10}


def nth_weekday(y,m,weekday,n):
 d=date(y,m,1)
 return d+timedelta(days=(weekday-d.weekday())%7+7*(n-1))


@lru_cache(None)
def calendars(last_year=2036):
 fed=set();market=set()
 for y in range(2026,last_year+1):
  for m,d in [(1,1),(6,19),(7,4),(11,11),(12,25)]:
   a=date(y,m,d);fed.add(a)
   if a.weekday()==6:fed.add(a+timedelta(days=1))
  for m,week,n in [(1,0,3),(2,0,3),(9,0,1),(10,0,2),(11,3,4)]:fed.add(nth_weekday(y,m,week,n))
  a=date(y,5,31);fed.add(a-timedelta(days=a.weekday()))
  market.add(easter(y)-timedelta(days=2))
  for m,d in [(6,19),(7,4),(12,25)]:
   a=date(y,m,d)
   if a.weekday()==5:market.add(a-timedelta(days=1))
 market|=fed
 euro=fed|set(holidays.country_holidays('GB',subdiv='ENG',years=range(2026,last_year+1)))|set(holidays.financial_holidays('ECB',years=range(2026,last_year+1)))
 return fed,market,euro


def following(d,cal):
 while d.weekday()>=5 or d in cal:d+=timedelta(days=1)
 return d


def preceding(d,cal):
 d-=timedelta(days=1)
 while d.weekday()>=5 or d in cal:d-=timedelta(days=1)
 return d


def boundaries(end):
 d=START
 while d<=end:
  yield d
  if d.day==15:d=d.replace(day=monthrange(d.year,d.month)[1])
  else:d=(d+timedelta(days=1)).replace(day=15)


def rate_curve(templates,future,stress_at):
 """Monthly July16-type reference periods; downward step <=25 bp per month.

 Fixed 3% SOFR scenario floor. Stress rate reacts to lagged, already observed
 stress, and reaches a supplied plateau. No rate reduction after payment failure
 occurs because the simulation terminates at its first failure.
 """
 r=.12
 for t in templates:
  record=date.fromisoformat(t['record_date'])
  if record.day==15 and record>=date(2026,9,15):
   # Rate determination uses conditions at least one complete period earlier.
   signal_date=record-timedelta(days=20)
   target=max(.03,future['strc_base_rate']+future['strc_stress_spread']*stress_at(signal_date))
   r=max(target,r-.0025)
  t['annual_rate']=float(r)


def schedule(base,future,end,stress_at):
 """Return opening, payments, STRC terms and conservative possible put dates."""
 fed,market,euro=calendars()
 opening=deepcopy(base['opening'])
 originals={p['id']:deepcopy(p) for p in base['payments']}
 oldclaims={c['id']:c for c in opening['claims']}
 original_first={k:next((p for p in base['payments'] if p['claim_id']==k and p['kind']=='interest'),None) for k in DEBT}
 payments=[];possible={};claims=[]
 for claim in opening['claims']:
  ident=claim['id']
  if ident not in DEBT:
   claims.append(claim);continue
  spec=DEBT[ident]
  branch=future['put_fraction']
  portions=[('put',branch),('maturity',1-branch)]
  for branch_name,fraction in portions:
   if fraction==0:continue
   c=deepcopy(claim)
   if 0<branch<1:c['id']=ident+'_'+branch_name
   c['face_native']*=fraction;c['accrued_native']*=fraction
   claims.append(c)
   nominal=date.fromisoformat(spec[branch_name]);cash=following(nominal,fed)
   possible[c['id']]=[str(following(date.fromisoformat(spec[k]),fed)) for k in ['put','maturity']]
   payments.append(dict(id=c['id']+'_principal',claim_id=c['id'],kind='principal',payment_date=str(cash),amount_native=c['face_native'],note='Cash repayment branch '+branch_name+'; no automatic conversion or refinancing'))
   if spec['rate']==0:continue
   dates=[date(y,m,spec['day']) for y in range(2026,2033) for m in spec['months']]
   dates=sorted(d for d in dates if START<d<=nominal)
   prev=date(2026,3,15) if spec['months']==[3,9] else date(2026,6,15)
   for i,d in enumerate(dates):
    amount=c['face_native']*spec['rate']/2
    pay=dict(id=c['id']+'_coupon_'+str(d),claim_id=c['id'],kind='interest',payment_date=str(following(d,fed)),amount_native=amount,accrual_start=str(prev),accrual_end=str(d),opening_credit_native=c['accrued_native'] if i==0 else 0.)
    payments.append(pay);prev=d
 opening['claims']=claims
 # Preserve the source's explicit small secured-loan approximation unchanged.
 payments.extend(deepcopy(p) for p in base['payments'] if p['claim_id']=='other_secured')
 possible['other_secured']=['2026-12-31']
 for ident,rate in PREF_RATES.items():
  prev=START
  for y in range(2026,end.year+2):
   for m in [3,6,9,12]:
    d=date(y,m,monthrange(y,m)[1])
    if d<=START or d>end+timedelta(days=550):continue
    cal=euro if ident=='STRE' else fed
    payments.append(dict(id=ident+'_dividend_'+str(d),claim_id=ident,kind='dividend',payment_date=str(following(d,cal)),amount_native=oldclaims[ident]['face_native']*rate/4,accrual_start=str(prev),accrual_end=str(d),opening_credit_native=0.,declared=True,note='Conditional cash declaration; constant stated principal and fixed rate'))
    prev=d
 # Beyond-horizon calendar also supports 18-month policy look-ahead, without
 # treating future realized rates as manager information.
 bs=list(boundaries(end+timedelta(days=570)))
 templates=[dict(id='STRC_dividend_'+str(b),record_date=str(a),accrual_end=str(b),payment_date=str(following(b,fed)),annual_rate=.12) for a,b in zip(bs,bs[1:])]
 rate_curve(templates,future,stress_at)
 for t in templates:
  original=originals.get(t['id'])
  opening_credit=original.get('opening_credit_native',0) if original else 0
  amount=original['amount_native'] if opening_credit else opening['strc_shares']*100*t['annual_rate']/24
  payments.append(dict(id=t['id'],claim_id='STRC',kind='dividend',payment_date=t['payment_date'],amount_native=amount,accrual_start=t['record_date'],accrual_end=t['accrual_end'],opening_credit_native=opening_credit,declared=True,note='Original shares; protected opening declared credits; scenario rate thereafter'))
 terms=dict(claim_id='STRC',stated_amount_usd=100,opening_annual_rate=.12,templates=templates,business_holidays=sorted(str(d) for d in fed))
 return opening,sorted(payments,key=lambda p:(p['payment_date'],p['id'])),terms,possible
