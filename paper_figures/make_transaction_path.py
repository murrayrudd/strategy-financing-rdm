from pathlib import Path
import gzip, json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT=Path(__file__).parent
DATA=ROOT.parent/'rdm_study/outputs'
OUT=ROOT/'generated_path'; OUT.mkdir(exist_ok=True)
R={p:json.load(gzip.open(DATA/f'witness_{p}.json.gz')) for p in ['liquidity_cap','anticipatory_12']}
summary=json.loads((DATA/'witness_summary.json').read_text())
start=pd.Timestamp('2026-06-30'); end=pd.Timestamp('2031-06-30')
closed0=pd.Timestamp(summary['closure_start']);closed1=pd.Timestamp(summary['closure_end'])
stop=pd.Timestamp('2028-03-01')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':9,'axes.labelsize':8,
 'xtick.labelsize':7,'ytick.labelsize':7,'axes.spines.top':False,'axes.spines.right':False,
 'pdf.fonttype':42,'svg.fonttype':'none'})
fig,axes=plt.subplots(3,2,figsize=(7.2,6.6),sharex=True)
axes=axes.ravel()
series={}
for p,r in R.items():
 snaps=[r['initial_snapshot']]+r['snapshots']
 a=pd.DataFrame([dict(date=pd.Timestamp(s['state']['asof']),btc=s['state']['btc'],strc=s['state']['strc_shares'],liquid=s['liquid_assets_usd'],floor=s['reserve_floor_usd']) for s in snaps])
 series[p]=a[a.date<=end]
 assert r['configuration']['initial_point']['btc_price_usd']>0
assert R['liquidity_cap']['failure']['date']=='2028-03-01'
points=R['anticipatory_12']['configuration']['path']
initial=R['anticipatory_12']['configuration']['initial_point']
ep=pd.DataFrame([initial]+points);ep['date']=pd.to_datetime(ep['date']);ep=ep[ep.date<=end]
for ax,col,title in [(axes[0],'btc_price_usd','a  Bitcoin price'),(axes[1],'multiple','b  Valuation multiplier')]:
 ax.plot(ep.date,ep[col]/ep[col].iloc[0],color='.15',lw=1.35)
 ax.set_ylabel('Opening = 1');ax.set_title(title,loc='left',fontweight='bold')
 ax.axhline(1,color='.65',lw=.55,ls=':')
for p,color,ls in [('liquidity_cap','#737373','--'),('anticipatory_12','#111111','-')]:
 a=series[p]
 for ax,col in [(axes[2],'btc'),(axes[3],'strc')]:
  y=a[col]/a[col].iloc[0]
  ax.step(a.date,y,where='post',color=color,ls=ls,lw=1.3)
  if p=='liquidity_cap':ax.scatter(a.date.iloc[-1],y.iloc[-1],marker='X',s=35,color=color,zorder=6)
 axes[4].step(a.date,a.liquid/1e9,where='post',color=color,ls=ls,lw=1.25)
 axes[4].step(a.date,a.floor/1e9,where='post',color=color,ls=':',lw=1)
 if p=='liquidity_cap':axes[4].scatter(a.date.iloc[-1],a.liquid.iloc[-1]/1e9,marker='X',s=35,color=color,zorder=6)
axes[2].set_title('c  Bitcoin holdings',loc='left',fontweight='bold');axes[2].set_ylabel('Opening = 1')
axes[3].set_title('d  STRC shares outstanding',loc='left',fontweight='bold');axes[3].set_ylabel('Opening = 1')
axes[4].set_title('e  Liquid assets and required reserve',loc='left',fontweight='bold');axes[4].set_ylabel('$ billion')
for p,color,ls in [('liquidity_cap','#737373','--'),('anticipatory_12','#111111','-')]:
 r=R[p];dates=[start];amounts=[0.];total=0.
 for e in r['ledger']:
  if pd.Timestamp(e['date'])>end:break
  if e['action']=='issue_common_atm':
   assert e['date']==e['details']['settlement_date']
   total+=e['details']['gross_usd']-e['details']['fee_usd'];dates.append(pd.Timestamp(e['date']));amounts.append(total/1e9)
 dates.append(min(end,pd.Timestamp(r['snapshots'][-1]['date'])));amounts.append(total/1e9)
 axes[5].step(dates,amounts,where='post',color=color,ls=ls,lw=1.3)
 if p=='liquidity_cap':axes[5].scatter(dates[-1],amounts[-1],marker='X',s=35,color=color,zorder=6)
 assert total>0, 'Verify common receipt action names before charting'
axes[5].set_title('f  Cumulative common cash receipts',loc='left',fontweight='bold');axes[5].set_ylabel('$ billion, net of fees')
for ax in axes:
 ax.axvspan(closed0,closed1,color='.91',zorder=-5)
 ax.axvline(stop,color='.55',lw=.7,ls=':')
 ax.set_xlim(start,end);ax.grid(axis='y',color='.9',lw=.5)
 ax.xaxis.set_major_locator(mdates.YearLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
axes[4].annotate('P8 payment stop\n1 Mar 2028',xy=(stop,series['liquidity_cap'].liquid.iloc[-1]/1e9),
 xytext=(pd.Timestamp('2029-03-01'),3.7),fontsize=7,arrowprops={'arrowstyle':'->','lw':.7,'color':'.35'})
handles=[Line2D([0],[0],color='.45',ls='--',label='P8 Cash and STRC cap'),Line2D([0],[0],color='.07',label='P9 Advance cash funding'),
 Patch(facecolor='.91',label='Financing closed'),Line2D([0],[0],color='.45',ls=':',label='Required reserve in panel e'),
 Line2D([0],[0],color='.45',marker='X',ls='',label='P8 payment stop')]
fig.legend(handles=handles,frameon=False,ncol=2,loc='lower center',bbox_to_anchor=(.5,.015),fontsize=7.5)
fig.subplots_adjust(left=.09,right=.98,top=.96,bottom=.18,hspace=.35,wspace=.32)
for ext in ['png','svg','pdf']:fig.savefig(OUT/f'Figure_4_Transaction_path.{ext}',dpi=350,facecolor='white')
plt.close(fig)
