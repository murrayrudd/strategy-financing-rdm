"""Reproduce the figure series from the accompanying manuscript summary data.

Run: python make_figures.py
Dependencies: matplotlib, numpy. No model runs or internet access are required.
"""
from pathlib import Path
import csv, json, re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'figures'; OUT.mkdir(exist_ok=True)
for ext in ['png','pdf','svg']:(OUT/ext).mkdir(exist_ok=True)
plt.rcParams.update({
    'font.family':'DejaVu Sans', 'font.size':8.5, 'axes.labelsize':8.5,
    'axes.titlesize':9, 'xtick.labelsize':8, 'ytick.labelsize':8,
    'legend.fontsize':8, 'axes.linewidth':.65, 'lines.linewidth':1.35,
    'xtick.major.width':.6,'ytick.major.width':.6,
    'xtick.major.size':3,'ytick.major.size':3,
    'axes.spines.top':False,'axes.spines.right':False,
    'axes.edgecolor':'.25','text.color':'.1','axes.labelcolor':'.1',
    'xtick.color':'.25','ytick.color':'.25',
    'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none',
    'figure.facecolor':'white','savefig.facecolor':'white',
    'hatch.linewidth':.45,
})

def read(key):
    with (ROOT/'data'/f'table_{key}.csv').open() as f:return list(csv.DictReader(f))
def lookup(key):return {r['Policy']:r for r in read(key)}
def count(s):return int(s.split(' (')[0].replace(',',''))
def pct(v,n=2000):return 100*float(v)/n
def fmt(v,d=1):return str(Decimal(str(v)).quantize(Decimal('1').scaleb(-d),rounding=ROUND_HALF_UP))
def stat(s):return [float(v) for v in re.findall(r'\d+(?:\.\d+)?',s)]
def clean(ax,grid=True):
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y',length=0)
    if grid:ax.grid(axis='x',color='.9',lw=.5,zorder=0)
    ax.set_axisbelow(True)
def panel(ax,letter,title):
    ax.set_title(f'{letter}  {title}',loc='left',pad=11,fontweight='bold')
def save(fig,name):
    for ext in ['pdf','svg','png']:
        target=OUT/ext/f'{name}.{ext}'
        tmp=target.with_name(target.name+'.tmp')
        fig.savefig(tmp,format=ext,dpi=600 if ext=='png' else 150)
        tmp.replace(target)
    plt.close(fig)
def date(s):return mdates.date2num(datetime.fromisoformat(s))

CAPTIONS=[]
def caption(name,title,text,placement,source):
    CAPTIONS.append({'file':name,'title':title,'caption':text,'placement':placement,'source':source})

# Figure 1: actual study dates plus a schematic corporate event sequence.
fig=plt.figure(figsize=(7.2,6.5))
ax=fig.add_axes([.18,.59,.78,.32])
start=date('2026-06-30');end=date('2033-06-30')
ax.hlines(2,start,end,color='.15',lw=2)
check=['2026-06-30','2027-09-30','2029-06-30','2031-06-30','2033-06-30']
labs=['Opening\nJun 2026','Checkpoint\nSep 2027','Checkpoint\nJun 2029','Primary endpoint\nJun 2031','Longer endpoint\nJun 2033']
for x,l in zip(check,labs):
    ax.plot(date(x),2,'o',color='.1',ms=4)
    ax.text(date(x),2.25,l,ha='center',va='bottom',fontsize=7.3)
for y,yr in [(1,2031),(0,2033)]:
    a=date(f'{yr}-06-30');b=date(f'{yr+1}-06-30')
    ax.plot([a,a],[2,y],color='.5',lw=.75,ls=':')
    ax.plot([a,b],[y,y],color='.2',lw=2,ls='--')
    ax.plot([a,b],[y,y],ls='none',marker='s',ms=4,mfc='white',mec='.15')
    ax.text((a+b)/2,y+.12,'No new issuance',ha='center',va='bottom',fontsize=7.3)
ax.set_xlim(date('2026-03-01'),date('2034-11-01'));ax.set_ylim(-.5,3.2)
ax.set_yticks([2,1,0],['Corporate path','2031 branch','2033 branch'])
ax.xaxis.set_major_locator(mdates.YearLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
clean(ax);panel(ax,'a','Study horizon and separate one-year closure branches')

ax=fig.add_axes([.03,.055,.94,.465]);ax.set_xlim(0,10);ax.set_ylim(0,5.8);ax.axis('off')
ax.text(0,5.55,'b  Corporate event sequence',fontweight='bold',fontsize=9)
def box(x,y,w,h,txt,fc='white'):
    p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.05,rounding_size=0.08',facecolor=fc,edgecolor='.3',lw=.75)
    ax.add_patch(p);ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=7.6,linespacing=1.4)
def arrow(a,b,ls='-',style='-|>',rad=0):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle=style,mutation_scale=9,lw=.8,color='.3',linestyle=ls,connectionstyle=f'arc3,rad={rad}'))
box(.15,4.2,9.55,.64,'Same external Bitcoin, valuation, and financing conditions for each compared policy',fc='.95')
for x in [1.55,5,8.45]:arrow((x,4.16),(x,3.73))
box(.15,2.8,2.8,.9,'Receive earlier financing\nRecord accruals and\noperating receipts')
box(3.6,2.8,2.8,.9,'Evaluate financing\nCommit new placements\nsubject to access and limits')
box(7.05,2.8,2.8,.9,'Use permitted liquidity\nSettle scheduled payments')
arrow((3,3.25),(3.55,3.25));arrow((6.45,3.25),(7,3.25))
box(.15,.78,2.8,.9,'Next event\nUpdate prices, balances,\nand commitments')
box(3.6,.78,2.8,.9,'Restore reserves if possible\nBuy Bitcoin with eligible\nfinancing receipts')
box(7.05,.78,2.8,.9,'Payment blocked?\nYes: stop the path\nNo: continue')
arrow((8.45,2.75),(8.45,1.73));arrow((7,1.23),(6.45,1.23));arrow((3.55,1.23),(3,1.23))
arrow((1.55,1.73),(1.55,2.75))
ax.plot([5,5,1.55],[2.75,2.2,2.2],ls='--',color='.4',lw=.8)
arrow((1.55,2.2),(1.55,2.75),ls='--')
ax.text(5.0,2.0,'New placements deliver on the next business day',ha='center',va='top',fontsize=7.2)
ax.text(5,.22,'Check payment continuity and reserve compliance through each checkpoint',ha='center',fontsize=7.5)
save(fig,'Figure_1_Study_setup')
caption('Figure_1_Study_setup','Figure 1. Study timing and corporate decisions.',
    'Panel a shows the June 2026 opening, four evaluation dates, and separate one-year branches that close both common and STRC issuance. The branches also receive a closure-plus-stress variant. The opening uses information available through August 3, 2026. Panel b shows the event sequence schematically. Each policy receives the same external future, but its transactions change later balances and funding needs. New financing commitments deliver on the next business day and cannot pay an obligation at the commitment event. Funded success requires payment completion and reserve compliance throughout the path.',
    'Methods: after Corporate balances and transaction mechanics.','Methods: Decision framework and study horizon; Corporate balances and transaction mechanics; Appendix A4.')

# Figure 2: selected policy trajectories; points are the reported checkpoints.
T4=lookup('4');T5=lookup('5')
fig,ax=plt.subplots(figsize=(7.2,4.1));fig.subplots_adjust(left=.10,right=.97,bottom=.25,top=.89)
cols=['Sep 2027','Jun 2029','Jun 2031','Jun 2033'];x=[date(z) for z in check[1:]]
policies=['Reference 100','BPS 100','Sales permission only','Advance cash funding','Advance funding and sales']
styles=[('v',':','.65','white'),('o','-','.15','white'),('s','--','.5','white'),('^','-.','.3','white'),('D','-','.05','.05')]
for p,(m,ls,c,fc) in zip(policies,styles):
    vals=[pct(count(T4[p][k])) for k in cols]
    ax.plot(x,vals,marker=m,ls=ls,color=c,mfc=fc,mec=c,ms=5,label=p,zorder=3)
ax.set_xticks(x,['Sep 2027','Jun 2029','Jun 2031','Jun 2033'])
ax.set_ylim(0,104);ax.set_yticks(range(0,101,20));ax.set_ylabel('Funded success (% of 2,000 futures)')
ax.grid(axis='y',color='.88',lw=.5);ax.set_axisbelow(True)
ax.set_title('Longer horizons expose financing failures',loc='left',fontweight='bold',pad=12)
fig.legend(loc='lower center',bbox_to_anchor=(.54,.015),ncol=2,frameon=False,columnspacing=2)
save(fig,'Figure_2_Horizon')
caption('Figure_2_Horizon','Figure 2. Funded success across the study horizon.',
    'The selected policies meet the payment and reserve target in nearly all futures at September 2027. Their funded shares separate as later commitments come due. Each point uses the same 2,000 futures; lines connect reported checkpoints and do not represent observations between them. Funded success requires all scheduled payments and reserve compliance throughout the path. BPS denotes the Bitcoin-per-share issuance screen. The cash-and-STRC-cap policy has the same funded counts as BPS 100 at all four checkpoints. Shares describe the explored design, not probabilities of future corporate outcomes.',
    'Results: after Table 4 or in place of its selected-policy comparison.','Table 4; policy definitions in Table 2.')

# Figure 3: partitions of the same denominator isolate payment stops and breaches.
component=['Cash and STRC cap','Sales permission only','Advance cash funding','Advance funding and sales']
labels=['Cash and STRC cap','Sales permission only','Advance cash funding','Advance funding\nand sales']
fresh={r['Policy']:r for r in read('8') if r['Set']=='Fresh component'}
fig,axs=plt.subplots(1,2,figsize=(7.2,3.75),sharey=True);fig.subplots_adjust(left=.235,right=.98,bottom=.27,top=.86,wspace=.12)
for ax,n,title,fresh_flag in zip(axs,[2000,512],['Original design (n = 2,000)','Fresh component test (n = 512)'],[False,True]):
    funded=np.array([count(fresh[p]['2031 funded']) if fresh_flag else count(T4[p]['Jun 2031']) for p in component])
    payments=np.array([count(fresh[p]['2031 payments']) if fresh_flag else count(T5[p]['Payments']) for p in component])
    parts=[funded,payments-funded,n-payments]
    assert all(np.all(z>=0) for z in parts) and np.all(sum(parts)==n)
    left=np.zeros(4)
    for j,(vals,fc,hat) in enumerate(zip(parts,['.25','.83','white'],['','','///'])):
        width=100*vals/n
        ax.barh(range(4),width,left=left,height=.55,color=fc,edgecolor='.3',linewidth=.55,hatch=hat,zorder=3)
        for y,(v,l) in enumerate(zip(width,left)):
            if v>=6:ax.text(l+v/2,y,fmt(v),ha='center',va='center',fontsize=7,color='white' if j==0 else '.1')
        left+=width
    ax.set_xlim(0,100);ax.set_xticks([0,25,50,75,100]);ax.set_xlabel('Share of futures (%)')
    clean(ax,False);panel(ax,'b' if fresh_flag else 'a',title)
axs[0].set_yticks(range(4),labels);axs[0].invert_yaxis()
fig.legend(handles=[Patch(fc='.25',ec='.3',label='Funded success'),Patch(fc='.83',ec='.3',label='Payments complete; reserve breach'),Patch(fc='white',ec='.3',hatch='///',label='Payment stop')],loc='lower center',bbox_to_anchor=(.56,.018),ncol=1,frameon=False,handlelength=2)
save(fig,'Figure_3_Policy_components')
caption('Figure_3_Policy_components','Figure 3. Different effects of advance funding and sale permission at June 2031.',
    'Each bar partitions all futures into three mutually exclusive outcomes: funded success; completed payments with at least one reserve breach; and a payment stop. All four policies retain cash protection and the STRC principal cap. Adding sale permission mainly reduces payment stops. Advance funding mainly expands the set that completes payments without a reserve breach. Panel a uses the original 2,000 futures. Panel b uses the later 512-future component test. Segment labels show percentages where space permits. A payment-stop path can also contain a reserve breach; it appears only in the payment-stop segment.',
    'Results: after the four-policy component comparison.','Tables 4, 5, and 8. Segments derived as funded, payments minus funded, and denominator minus payments.')

# Figure 4: full-domain objective attainment plus explicit gains and losses.
baseline='BPS 100';combined='Advance funding and sales'
targets=['Funded success','Nominal value','5% annual return','Bitcoin per share']
base=[count(T4[baseline]['Jun 2031'])]+[count(T5[baseline][k]) for k in ['Nominal value','5% annual return','Bitcoin per share']]
rev=[count(T4[combined]['Jun 2031'])]+[count(T5[combined][k]) for k in ['Nominal value','5% annual return','Bitcoin per share']]
pairs=[r for r in read('6') if r['Policy']==combined]
gains=[int(r['Gains']) for r in pairs]+[0];losses=[int(r['Losses']) for r in pairs]+[2]
assert [a-b for a,b in zip(rev,base)]==[a-b for a,b in zip(gains,losses)]
fig,axs=plt.subplots(1,2,figsize=(7.2,3.5),sharey=True);fig.subplots_adjust(left=.22,right=.96,bottom=.24,top=.84,wspace=.24)
ax=axs[0]
for i,(b,r) in enumerate(zip(base,rev)):
    ax.plot([pct(b),pct(r)],[i,i],color='.65',lw=1.2,zorder=2)
    ax.plot(pct(b),i,'o',ms=5.5,mfc='white',mec='.15',zorder=3)
    ax.plot(pct(r),i,'D',ms=4.8,color='.1',zorder=4)
    ax.text(pct(b),i+.25,fmt(pct(b)),ha='center',va='center',fontsize=7.2)
    ax.text(pct(r),i-.25,fmt(pct(r)),ha='center',va='center',fontsize=7.2,fontweight='bold')
ax.set_yticks(range(4),targets);ax.set_ylim(3.55,-.6);ax.set_xlim(-3,100)
ax.set_xticks([0,25,50,75,100]);ax.set_xlabel('Share of 2,000 futures (%)');clean(ax);panel(ax,'a','Target attainment')
ax=axs[1]
ax.axvline(0,color='.4',lw=.75)
ax.barh(range(4),gains,height=.48,color='.3',edgecolor='.3',zorder=3)
ax.barh(range(4),-np.array(losses),height=.48,color='white',edgecolor='.3',hatch='///',lw=.7,zorder=3)
for i,(g,l) in enumerate(zip(gains,losses)):
    ax.text(g+9,i,str(g),va='center',fontsize=8)
    ax.text(-l-9,i,str(l),va='center',ha='right',fontsize=8)
ax.set_xlim(-65,430);ax.set_xticks([0,100,200,300,400]);ax.set_xlabel('Matched futures');clean(ax);panel(ax,'b','Gains and losses')
fig.legend(handles=[Line2D([],[],ls='',marker='o',mfc='white',mec='.15',label='BPS 100'),Line2D([],[],ls='',marker='D',color='.1',label='Advance funding and sales'),Patch(fc='.3',label='Gain'),Patch(fc='white',ec='.3',hatch='///',label='Loss')],loc='lower center',bbox_to_anchor=(.56,.025),ncol=2,frameon=False,columnspacing=1.7)
save(fig,'Figure_4_Objectives_and_paired_effects')
caption('Figure_4_Objectives_and_paired_effects','Figure 4. Funding and shareholder targets give different policy assessments at June 2031.',
    'Panel a compares target shares under BPS 100 and the combined advance-funding-and-sales revision. Nominal value and the 5% annual return target also require funded success and defined quotes. Bitcoin-per-share preservation also requires funded success. Panel b counts matched futures in which the combined revision alone succeeds (gains) or BPS 100 alone succeeds (losses). These are changes in target attainment, not investment returns. All comparisons use 2,000 futures. The larger funded set does not imply gains in every future or attainment of every shareholder objective.',
    'Results: Outcome measures and paired effects, after Table 6.','Tables 4, 5, and 6; the two lost BPS successes are reported in the Table 6 note.')

# Figure 5: no invented distributions: paired summary points only.
B3={(r['Policy'],r['Year']):r for r in read('B3')}
with (ROOT/'data'/'conditional_holdings_issuance.csv').open() as f:narr={r['Policy']:r for r in csv.DictReader(f)}
metrics=[
 ('Gross common issuance','USD billion',lambda p:float(narr[p]['Median common issuance USD bn']),(0,14),[0,5,10],2),
 ('Bitcoin holdings','Thousand Bitcoin',lambda p:float(narr[p]['Median Bitcoin holdings'])/1000,(0,900),[0,300,600,900],1),
 ('Common share growth','Change from opening (%)',lambda p:float(B3[p,'2031']['Share growth %']),(0,40),[0,10,20,30,40],1),
 ('Bitcoin per share','Change from opening (%)',lambda p:float(B3[p,'2031']['BPS change %']),(-40,0),[-40,-30,-20,-10,0],1),
 ('Common return','Change from opening (%)',lambda p:float(B3[p,'2031']['Common return %']),(0,30),[0,10,20,30],1),
 ('Return regret at the 90th percentile','Percentage points',lambda p:float(B3[p,'2031']['Regret p90 pp']),(0,40),[0,10,20,30,40],1)]
fig,axs=plt.subplots(3,2,figsize=(7.2,5.3));fig.subplots_adjust(left=.07,right=.96,bottom=.16,top=.9,hspace=1.1,wspace=.3)
for ax,(i,m) in zip(axs.flat,enumerate(metrics)):
    title,unit,func,lim,ticks,d=m;b,r=[func(p) for p in [baseline,combined]]
    ax.plot([b,r],[0,0],color='.65',lw=1.3)
    ax.plot(b,0,'o',mfc='white',mec='.15',ms=6,zorder=3)
    ax.plot(r,0,'D',color='.1',ms=5,zorder=4)
    ax.text(b,.27,fmt(b,d),ha='center',va='center',fontsize=8)
    ax.text(r,-.3,fmt(r,d),ha='center',va='center',fontsize=8,fontweight='bold')
    ax.set_xlim(lim);ax.set_xticks(ticks);ax.set_ylim(-.6,.65);ax.set_yticks([])
    ax.set_xlabel(unit);clean(ax);panel(ax,chr(97+i),title)
fig.legend(handles=[Line2D([],[],ls='',marker='o',mfc='white',mec='.15',label='BPS 100'),Line2D([],[],ls='',marker='D',color='.1',label='Advance funding and sales')],loc='lower center',bbox_to_anchor=(.5,.015),ncol=2,frameon=False)
save(fig,'Figure_5_Shareholder_tradeoffs')
caption('Figure_5_Shareholder_tradeoffs','Figure 5. Financing and shareholder tradeoffs on matched completed paths at June 2031.',
    'Both policies are evaluated on the same 1,345 futures that all eight initial policies and both revisions completed with defined daily quotes. Panels a-e report medians; panel f reports the 90th percentile of return regret relative to the best of those ten policies within each future. The combined revision raises more common capital and retains more Bitcoin, but increases the share count and produces a larger median decline in Bitcoin per share. These are separate summary statistics, not one representative trajectory. The comparison excludes stopped or undefined paths and can include reserve breaches.',
    'Results: after the conditional return comparison; alternatively Appendix B2.','Appendix B2 narrative and Table B3. Holdings are displayed in thousands of Bitcoin.')

# Figure 6: means only; ranges are smaller than the markers at print size.
rows=read('9');names=[r['Policy'] for r in rows]
display=[n.replace('Advance funding and sales','Advance funding\nand sales') for n in names]
fig,axs=plt.subplots(1,2,figsize=(7.2,5.3),sharey=True);fig.subplots_adjust(left=.235,right=.98,bottom=.18,top=.9,wspace=.14)
for ax,j,year in zip(axs,['June 2031 mean and range %','June 2033 mean and range %'],[2031,2033]):
    for y,r in enumerate(rows):
        mean,lo,hi=stat(r[j]);original=pct(count(T4[r['Policy']][f'Jun {year}']))
        ax.plot(mean,y-.09,marker='o',ms=3.8,color='.1',ls='',zorder=4)
        ax.plot(original,y+.12,marker='s',mfc='white',mec='.45',ms=4,ls='',zorder=3)
    ax.set_xlim(35,95);ax.set_xticks([40,50,60,70,80,90]);ax.set_xlabel('Funded success (%)')
    clean(ax);panel(ax,'a' if year==2031 else 'b',f'June {year}')
axs[0].set_yticks(range(len(names)),display);axs[0].set_ylim(len(names)-.4,-.7)
fig.legend(handles=[Line2D([],[],ls='',marker='s',mfc='white',mec='.45',label='Original 2,000-future design'),Line2D([],[],ls='',marker='o',ms=4,color='.1',label='Mean of three 10,000-future designs')],loc='lower center',bbox_to_anchor=(.56,.02),ncol=1,frameon=False)
save(fig,'Figure_6_Policy_replications')
caption('Figure_6_Policy_replications','Figure 6. Policy comparisons across independent samples.',
    'Open squares show funded shares in the original 2,000-future design. Filled circles show the reported means across three independent 10,000-future designs. Each design evaluates all eleven policies. The original design is excluded from those means. The advance-funding policies retain their funding advantage at both long endpoints. The replication ranges are too small to display clearly at this scale; Table 9 reports them numerically. The final tests passed the stated funded-share and primary paired-effect tolerances. PRIM case membership requires a separate assessment (Figure S1).',
    'Results: Independent Latin hypercube replications, after Table 9.','Tables 4 and 9. Means use the one-decimal values reported in Table 9.')

# Supplementary Figure S1: PRIM stability evaluated on a common probe set.
rows=read('B7');ylabs=['Funded failure\nFirst region','Funded failure\nRegion union','Nominal-value failure\nFirst region','Nominal-value failure\nRegion union']
fig,axs=plt.subplots(1,3,figsize=(7.2,3.5),sharey=True);fig.subplots_adjust(left=.23,right=.96,bottom=.18,top=.83,wspace=.25)
for ax,key,label,letter in zip(axs[:2],['Density mean and range %','Coverage mean and range %'],['Failure density','Failure coverage'],['a','b']):
    for y,r in enumerate(rows):
        mean,lo,hi=stat(r[key]);ax.errorbar(mean,y,xerr=[[mean-lo],[hi-mean]],fmt='o',ms=4,color='.15',capsize=2.5,lw=1.2)
    ax.set_xlim(0,100);ax.set_xticks([0,50,100]);ax.set_xlabel('Percent');clean(ax);panel(ax,letter,label)
ax=axs[2]
ax.axvline(.60,color='.4',ls='--',lw=.9)
for y,r in enumerate(rows):
    v=float(r['Minimum Jaccard']);ax.plot(v,y,'D',mfc='white' if v<.6 else '.15',mec='.15',ms=5)
    ax.text(v,y-.27,f'{v:.3f}',ha='center',fontsize=7.5)
ax.set_xlim(0,1.05);ax.set_xticks([0,.5,1]);ax.set_xlabel('Minimum Jaccard');clean(ax);panel(ax,'c','Case overlap')
ax.text(.60,-.72,'Required 0.60',ha='center',fontsize=7,color='.35')
axs[0].set_yticks(range(4),ylabs);axs[0].set_ylim(3.55,-.95)
save(fig,'Figure_S1_PRIM_stability')
caption('Figure_S1_PRIM_stability','Figure S1. Scenario-discovery stability differs across failure targets and regions.',
    'Three fits from independent 10,000-future samples are evaluated on the same original 2,000 futures, which were excluded from fitting. All results concern BPS 100 at June 2031. Panels a and b show the reported means and ranges of failure density and coverage. Panel c shows the minimum pairwise Jaccard overlap of selected cases. The first funding region falls below the prespecified 0.60 requirement, whereas the funding-region union and both nominal-value regions pass. Density measures failures inside a region; coverage measures the share of all failures captured. Ranges describe variation across fits, not confidence intervals.',
    'Appendix B5: after Table B7; cite from the convergence Results.','Table B7.')

# Supplementary Figure S2: maintain the full 2,000-future denominator on the axis.
rows=read('B4');policies=['Reference 100','BPS 100','Cash and STRC cap','Advance cash funding','Advance funding and sales']
fig,axs=plt.subplots(1,2,figsize=(7.2,3.65),sharey=True);fig.subplots_adjust(left=.235,right=.97,bottom=.25,top=.85,wspace=.13)
for ax,year in zip(axs,[2031,2033]):
    R={r['Policy']:r for r in rows if r['Branch year']==str(year)}
    for y,p in enumerate(policies):
        vals=[pct(count(R[p][k])) for k in ['Endpoint funded','Closure only','Closure plus stress']]
        ax.plot(vals,[y]*3,color='.6',lw=1,zorder=2)
        for v,m,fc in zip(vals,['o','^','D'],['white','.6','.1']):ax.plot(v,y,marker=m,mfc=fc,mec='.15',ms=4.8,ls='',zorder=3)
    ax.set_xlim(45,91);ax.set_xticks([50,60,70,80,90]);ax.set_xlabel('Funded (% of original 2,000 futures)');clean(ax)
    panel(ax,'a' if year==2031 else 'b',f'June {year} to June {year+1}')
axs[0].set_yticks(range(5),[p.replace('Advance funding and sales','Advance funding\nand sales') for p in policies]);axs[0].set_ylim(4.5,-.6)
fig.legend(handles=[Line2D([],[],marker='o',mfc='white',mec='.15',ls='',label='At branch start'),Line2D([],[],marker='^',mfc='.6',mec='.15',ls='',label='After closure only'),Line2D([],[],marker='D',color='.1',ls='',label='After closure plus stress')],loc='lower center',bbox_to_anchor=(.55,.025),ncol=2,frameon=False)
save(fig,'Figure_S2_Closure_tails')
caption('Figure_S2_Closure_tails','Figure S2. Funded success after a further year without new issuance.',
    'Each panel compares success at a long endpoint with success after one further year without common or STRC issuance. The stress variant gradually applies a 40% Bitcoin markdown and a 25% valuation-multiplier markdown. It also adds four percentage points to the STRC rate after its specified lag. All plotted shares retain the original 2,000-future denominator. Conditional retention rates instead divide by each policy\'s own starting successes. After June 2031, the combined revision retains 91.3% of its successes under closure plus stress, compared with 91.8% for BPS 100, while preserving the larger funded set.',
    'Appendix B3: after Table B4; cite from One year without new issuance.','Table B4 and Appendix A7.')

(ROOT/'captions.json').write_text(json.dumps(CAPTIONS,indent=2))
(ROOT/'Figure_captions.txt').write_text('\n\n'.join(c['title']+'\n'+c['caption']+'\nSource: '+c['source']+'\nSuggested placement: '+c['placement'] for c in CAPTIONS)+'\n')
print('Created',len(CAPTIONS),'figures in PDF, SVG, and 600 dpi PNG.')
