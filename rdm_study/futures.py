"""Reproducible exploratory futures; sampling frequencies are not probabilities."""
from datetime import date,timedelta
import numpy as np
import pandas as pd
from scipy.stats import qmc
from common import ROOT,REPO,START,TAIL,write_json,opening_market

N_DAYS=(TAIL-START).days+601
YEARS=np.arange(N_DAYS)/365.25
RANGES={
 'bitcoin_cagr':(-.25,.45),'valuation_factor':(.35,2.5),
 'shock_depth':(.15,.80),'shock_start':(.25,4.75),'recovery_years':(.4,3.),
 'closure_months':(0.,36.),'closure_threshold':(.20,.65),'capacity_scale':(.05,1.25),
 'strc_base_rate':(.10,.16),'strc_stress_spread':(0.,.06),'strc_discount':(0.,15.),
 'annual_operating_cashflow':(-300e6,100e6),'eur_terminal_factor':(.75,1.35),
 'valuation_stress_strength':(0.,1.2),'closure_start_independent':(.25,5.5)}


def designs(n,seed,phase):
 u=qmc.LatinHypercube(d=len(RANGES)+3,seed=seed).random(n)
 rows=[]
 for i,a in enumerate(u):
  r={k:float(lo+a[j]*(hi-lo)) for j,(k,(lo,hi)) in enumerate(RANGES.items())}
  r.update(future_id=f'{phase}_{i:04d}',phase=phase,seed=seed*10000+i,
           put_fraction=float(a[-3]>=.5),authorization_renewal=bool(a[-2]>=.5),
           dependence='linked' if a[-1]>=.5 else 'independent',family='stylized',
           historical_pool='none',repeated_shock=bool(i%2),generator='triangle')
  if phase=='main' and i%4==0:r.update(family='block',historical_pool='2014_2019')
  if phase=='challenge':
   if i%2==0:r.update(family='block',historical_pool='2020_2025')
   else:r.update(generator='plateau',repeated_shock=True)
  rows.append(r)
 return rows


def historical_returns(pool):
 p=REPO/'research/legacy_engine/historical_data/btc_priceusd_2014_2025.csv'
 d=pd.read_csv(p);d.columns=['date','price'];d['date']=pd.to_datetime(d.date)
 y=np.log(d.price.astype(float)).diff()
 mask=(d.date.dt.year<=2019) if pool=='2014_2019' else (d.date.dt.year>=2020)
 return y[mask].dropna().to_numpy()


def external_paths(future,opening_point=None):
 anchor=opening_market(opening_point)
 f=future;t=YEARS;rng=np.random.default_rng(f['seed'])
 logprice=np.log1p(f['bitcoin_cagr'])*t
 def pulse(onset,depth,recovery):
  fall=.20
  if f.get('generator')=='plateau':
   return np.interp(t,[0,onset,onset+fall,onset+fall+recovery*.6,onset+fall+recovery,t[-1]+1],[0,0,np.log1p(-depth),np.log1p(-depth),0,0])
  return np.interp(t,[0,onset,onset+fall,onset+fall+recovery,t[-1]+1],[0,0,np.log1p(-depth),0,0])
 if f['family']=='stylized':
  logprice+=pulse(f['shock_start'],f['shock_depth'],f['recovery_years'])
  if f['repeated_shock']:logprice+=pulse(f['shock_start']+2.8,.7*f['shock_depth'],.7*f['recovery_years'])
 elif f['family']=='block':
  source=historical_returns(f['historical_pool']);blocks=[]
  while sum(len(b) for b in blocks)<len(t)-1:
   start=int(rng.integers(0,len(source)-180));blocks.append(source[start:start+180])
  draws=np.concatenate(blocks)[:len(t)-1]
  noise=np.r_[0,np.cumsum(draws-draws.mean())]
  logprice+=noise
 elif f['family']=='historical':
  p=REPO/'research/legacy_engine/historical_data/btc_priceusd_2014_2025.csv'
  d=pd.read_csv(p);d.columns=['date','price'];d=d[d.date>=f['historical_start']]
  prices=d.price.to_numpy(float);need=(TAIL-START).days+1
  if len(prices)<need:raise ValueError('Historical interval too short')
  logprice=np.r_[np.log(prices[:need]/prices[0]),np.full(len(t)-need,np.log(prices[need-1]/prices[0]))]
 price=anchor['price']*np.exp(logprice)
 dd=1-price/np.maximum.accumulate(price)
 stress=np.clip(dd/.60,0,1)
 drift=np.log(f['valuation_factor'])*np.minimum(t/5,1)
 valuation=anchor['multiple']*np.exp(drift-(f['valuation_stress_strength']*stress if f['dependence']=='linked' else 0))
 closed=np.zeros(len(t),bool)
 if f['dependence']=='linked':
  inds=np.where(dd>=f['closure_threshold'])[0];onset=t[inds[0]] if len(inds) else t[-1]+1
 else:onset=f['closure_start_independent']
 if f['closure_months']>0:closed=(t>=onset)&(t<onset+f['closure_months']/12)
 cap=np.full(len(t),f['capacity_scale'])
 if f['dependence']=='linked':cap*=np.maximum(.10,1-.8*stress)
 cap[closed]=0
 fx=anchor['fx']['EUR']*np.exp(np.log(f['eur_terminal_factor'])*np.minimum(t/5,1))
 execution=100-f['strc_discount']*(stress if f['dependence']=='linked' else .5*(np.sin(t*1.7)**2))
 return dict(price=price,multiple=valuation,capacity=cap,fx=fx,execution=execution,stress=stress,drawdown=dd,closed=closed)


def main():
 a=designs(2000,1011,'main');b=designs(512,9023,'challenge')
 # These full historical paths overlap the resampling sources and are labeled
 # descriptive historical challenges, not independent validation observations.
 hs=[]
 for i,d in enumerate(pd.date_range('2014-01-01','2017-01-01',freq='3MS')):
  for branch in [0.,1.]:
   f=designs(1,500+i,'historical')[0]
   f.update(future_id=f'historical_{i:02d}_{int(branch)}',family='historical',historical_start=str(d.date()),put_fraction=branch,authorization_renewal=False,capacity_scale=1.,strc_base_rate=.12,strc_stress_spread=.02,annual_operating_cashflow=-60e6,eur_terminal_factor=1.)
   hs.append(f)
 write_json(ROOT/'inputs/futures_main.json',a)
 write_json(ROOT/'inputs/futures_challenge.json',b)
 write_json(ROOT/'inputs/futures_historical.json',hs)
 write_json(ROOT/'inputs/uncertainty_ranges.json',RANGES)
 print(len(a),len(b),len(hs))

if __name__=='__main__':main()
