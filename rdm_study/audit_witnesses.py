"""Independent sale-purpose and payment-cash audit of representative ledgers."""
import json,math
import pandas as pd
from common import ROOT,CORE,TAIL,write_json
from model import run
from metrics import independent_checks

def audit(r):
 payments={p['id']:p for p in r.configuration['payments']+r.generated_payments};claims={c['id']:c for c in r.configuration['opening']['claims']};points={p['date']:p for p in r.configuration['path']};previous=r.initial_snapshot['state'];errors=[];general=0.;sales=0;settlements=0
 def eq(a,b,label):
  errors.append(abs(a-b))
  if not math.isclose(a,b,rel_tol=2e-11,abs_tol=.002):raise AssertionError((label,a,b))
 for e in r.ledger:
  after=e['after'];p=points[e['date']];d=e['details']
  if e['action']=='sell_bitcoin_for_funding':
   sales+=1;gross=d['gross_usd'];net=gross*(1-r.configuration['policy']['btc_sale_cost_rate']-r.configuration['policy']['effective_sale_tax_cash_fraction'])
   eq(previous['btc']-after['btc'],gross/p['btc_price_usd'],'Sale inventory');eq(after['cash_usd']-previous['cash_usd'],net,'Sale cash');eq(net,d['general_use_net_usd']+d['distribution_net_usd']+d['reserve_build_net_usd'],'Sale purpose allocation')
   fraction=net/gross;general+=d['general_use_net_usd']/fraction
   if general>p['btc_general_use_gross_limit_usd']+.002:raise AssertionError('General sale authority exceeded')
  if e['action']=='settle_dated_commitments':
   settlements+=1;cash=max(0,-p['operating_cashflow_usd']);faces={}
   for ident in d['payment_ids']:
    pay=payments[ident]
    if pay.get('settlement','cash')=='cash':cash+=pay['amount_native']*p['fx_usd_per_unit'][claims[pay['claim_id']]['currency']]
    if pay['kind']=='principal':faces[pay['claim_id']]=faces.get(pay['claim_id'],0)-pay['amount_native']
   eq(previous['cash_usd']-after['cash_usd'],cash,'Payment cash')
   for k,v in faces.items():eq(e['face_changes_native'][k],v,'Principal retirement')
  if e['action']=='designate_reserve':eq(previous['cash_usd'],after['cash_usd'],'Reserve designation creates no cash')
  previous=after
 return dict(checks=len(errors),sales=sales,settlement_events=settlements,max_absolute_difference=max(errors,default=0),passed=True)

def main():
 fs=json.loads((ROOT/'inputs/futures_main.json').read_text());byid={f['future_id']:f for f in fs};d=pd.read_csv(ROOT/'outputs/all_main.csv');a=d[(d.horizon=='2031-06-30')&(d.policy=='anticipatory_sale')]
 ids=list(a.sort_values('bitcoin_sold',ascending=False).head(4).future_id)+['main_0001','main_0020','main_0932','main_0003'];records=[]
 for ident in dict.fromkeys(ids):
  for p in ['bps_100','anticipatory_12','anticipatory_sale']:
   r,_=run(byid[ident],p);independent_checks(r);records.append(dict(future_id=ident,policy=p,variant='normal',**audit(r)))
 for ident in ids[:2]:
  r,_=run(byid[ident],'anticipatory_sale',end=TAIL,closure_at=CORE,closure_stress=True);independent_checks(r);records.append(dict(future_id=ident,policy='anticipatory_sale',variant='extended_closure_audit',**audit(r)))
 write_json(ROOT/'outputs/transaction_witness_audits.json',records);print('Independent transaction witnesses',len(records),'passed')

if __name__=='__main__':main()
