"""Publication figures from retained complete matched results only."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import ROOT,CORE,LONG
from analyze import LABELS

SELECT=['reference_100','bps_100','liquidity_cap','anticipatory_12','anticipatory_sale']
SHORT={'reference_100':'Reference 100','bps_100':'BPS 100','liquidity_cap':'Cash + STRC cap','anticipatory_12':'Advance cash','anticipatory_sale':'Advance + sales'}
STYLE=[('0.7','s','--'),('0.25','o','-'),('0.5','^',':'),('0.1','D','--'),('0','v','-')]

def save(fig,name):
 fig.savefig(ROOT/'figures'/(name+'.png'),dpi=250,bbox_inches='tight',facecolor='white')
 fig.savefig(ROOT/'figures'/(name+'.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)

def main():
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.labelsize':9,'legend.fontsize':8,'svg.fonttype':'none'})
 out=ROOT/'outputs';d=pd.read_csv(out/'all_main.csv');horizons=sorted(d.horizon.unique());years=[2027.75,2029.5,2031.5,2033.5]
 fig,axes=plt.subplots(1,3,figsize=(6.7,3.3),sharey=True)
 for ax,col,title in zip(axes,['payments','funded','nominal_value'],['A  Payments','B  Payments and reserves','C  Nominal value']):
  for p,(color,marker,line) in zip(SELECT,STYLE):
   y=d[d.policy==p].groupby('horizon')[col].mean().reindex(horizons)*100
   ax.plot(years,y,color=color,marker=marker,linestyle=line,lw=1.25,ms=4,label=SHORT[p])
  ax.set_title(title,loc='left',fontsize=9);ax.set_xticks(years,['Sep 2027','Jun 2029','Jun 2031','Jun 2033'],rotation=35,ha='right');ax.set_ylim(0,102);ax.grid(axis='y',alpha=.2)
 axes[0].set_ylabel('Share of 2,000 designed futures (%)');axes[0].legend(loc='lower left',frameon=False)
 fig.tight_layout();save(fig,'01_horizon_performance')
 # Matched policy gains and losses are separate from marginal success rates.
 p=pd.read_csv(out/'all_main_paired.csv');g=p[(p.horizon==str(CORE))&(p.comparator=='bps_100')]
 fig,axes=plt.subplots(1,2,figsize=(6.7,3.3),sharey=True)
 selected=['reference_100','liquidity_cap','anticipatory_12','anticipatory_sale'];y=np.arange(len(selected))
 for ax,outcome,title in zip(axes,['funded','nominal_value'],['A  Payments and reserves','B  Nominal common value']):
  a=g[g.outcome==outcome].set_index('policy').loc[selected]
  ax.barh(y,a.gains,color='.2',label='Gains');ax.barh(y,-a.losses,color='.8',edgecolor='.2',hatch='///',label='Losses');ax.axvline(0,color='black',lw=.8)
  for i,(_,r) in enumerate(a.iterrows()):
   ax.text(r.gains+4,i,str(int(r.gains)),va='center',fontsize=8)
   if r.losses:ax.text(-r.losses-4,i,str(int(r.losses)),va='center',ha='right',fontsize=8)
  ax.set_title(title,loc='left',fontsize=10);ax.margins(x=.20);ax.grid(axis='x',alpha=.15)
 axes[0].set_yticks(y,[SHORT[p] for p in selected]);axes[0].invert_yaxis();axes[1].legend(frameon=False,loc='best');fig.supxlabel('Futures gained or lost relative to BPS 100',fontsize=9);fig.tight_layout();save(fig,'02_paired_policy_changes')
 # Primary PRIM first-box transfer; avoid suggesting a complete failure frontier.
 v=pd.read_csv(out/'prim_validation.csv');e=pd.read_csv(out/'prim_external_validation.csv');fig,axes=plt.subplots(1,2,figsize=(6.7,3.3),sharex=True,sharey=True)
 for ax,outcome,title in zip(axes,['funded','nominal_value'],['A  Funding failure region','B  Nominal value failure region']):
  m=(v.policy=='bps_100')&(v.horizon==str(CORE))&(v.outcome==outcome)&(v.box=='1')
  a=v[m]
  for split,marker,c in [('train','o','.65'),('holdout','s','.3')]:
   z=a[a.split==split].iloc[0];ax.scatter(z.coverage*100,z.density*100,marker=marker,s=60,c=c,label=split.title())
  z=e[(e.phase=='challenge')&(e.policy=='bps_100')&(e.horizon==str(CORE))&(e.outcome==outcome)&(e.box=='1')].iloc[0]
  ax.scatter(z.coverage*100,z.density*100,marker='^',s=65,c='black',label='Reserved challenge')
  ax.axhline(90,color='.6',ls=':',lw=1);ax.set_title(title,loc='left');ax.set_xlabel('Failure coverage (%)');ax.set_xlim(0,100);ax.set_ylim(0,100);ax.grid(alpha=.2)
 axes[0].set_ylabel('Failure density inside region (%)');axes[1].legend(frameon=False,loc='lower right');fig.tight_layout();save(fig,'03_prim_transfer')
 if (out/'tail_retention.csv').exists():
  t=pd.read_csv(out/'tail_retention.csv');fig,axes=plt.subplots(1,2,figsize=(6.7,3.9),sharey=True)
  for ax,prefix,title in zip(axes,['core','long'],['A  Closure after June 2031','B  Closure after June 2033']):
   for j,(s,label,col,hatch) in enumerate([('_closure','No new financing','.7',None),('_stress_closure','Closure plus market stress','.25','///')]):
    a=t[(t.variant==prefix+s)&(t.criterion=='funded')].set_index('policy').loc[SELECT]
    ax.bar(np.arange(len(SELECT))+(j-.5)*.35,a.conditional_retention*100,width=.35,color=col,edgecolor='black',lw=.5,hatch=hatch,label=label)
   ax.set_xticks(np.arange(len(SELECT)),[SHORT[p] for p in SELECT],rotation=35,ha='right');ax.set_ylim(0,102);ax.set_title(title,loc='left');ax.grid(axis='y',alpha=.2)
  axes[0].set_ylabel('Retention of endpoint funded successes (%)');handles,labels=axes[1].get_legend_handles_labels();fig.legend(handles,labels,frameon=False,loc='lower center',ncol=2);fig.tight_layout(rect=[0,.09,1,1]);save(fig,'04_financing_closure')
 # Selected structural sensitivities on a common 256-future subset.
 s=pd.read_csv(out/'sensitivity_paired.csv');ss=s[(s.horizon==str(CORE))&(s.outcome=='funded')]
 variants=['execution_floor_1e-06','execution_floor_1','face_valuation','market_value_capacity_2pct','half_puts'];names=['Price floor $0.000001','Price floor $1','Face valuation','2% market-value capacity','Half holder puts']
 a=ss.pivot(index='variant',columns='policy',values='variant_successes')-ss.pivot(index='variant',columns='policy',values='base_successes');a=a.reindex(index=variants,columns=SELECT)/256*100
 fig,ax=plt.subplots(figsize=(6.7,3.45));lim=max(1,np.nanmax(abs(a.to_numpy())));im=ax.imshow(a,cmap='Greys',vmin=-lim,vmax=lim,aspect='auto')
 for i in range(len(a)):
  for j in range(len(SELECT)):
   value=a.iloc[i,j];ax.text(j,i,f'{value:+.1f}',ha='center',va='center',color='white' if value>lim*.45 else 'black')
 ax.set_yticks(range(len(a)),names);ax.set_xticks(range(len(SELECT)),[SHORT[p] for p in SELECT],rotation=30,ha='right');ax.set_title('Change in funded share in percentage points',loc='left');fig.colorbar(im,ax=ax,fraction=.035,pad=.025,label='Percentage points');fig.tight_layout();save(fig,'05_structural_sensitivities')
 # Principal cash dates demonstrate why the original endpoint is incomplete.
 fig,ax=plt.subplots(figsize=(6.7,2.8))
 for name,label,marker,shade in [('principal_put_branch.csv','Full holder puts','o','.1'),('principal_maturity_branch.csv','No holder puts','s','.6')]:
  a=pd.read_csv(ROOT/'evidence'/name);a=a.groupby('payment_date').amount_native.sum();dates=pd.to_datetime(a.index)
  ax.vlines(dates,0,a/1e9,colors=shade,linewidth=2);ax.scatter(dates,a/1e9,color=shade,marker=marker,label=label,s=35)
 ax.axvline(pd.Timestamp('2027-09-30'),color='.4',ls=':',lw=1);ax.text(pd.Timestamp('2027-10-15'),2.07,'Original endpoint',fontsize=8)
 ax.set_ylabel('Principal cash payment ($ billion)');ax.set_ylim(0,2.2);ax.legend(frameon=False,loc='upper right');ax.grid(axis='y',alpha=.2);fig.tight_layout();save(fig,'06_principal_calendar')
 print('Available publication figures saved in PNG and SVG')

if __name__=='__main__':main()
