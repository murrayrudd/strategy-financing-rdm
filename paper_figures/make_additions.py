from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,FancyArrowPatch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
OUT=Path(__file__).resolve().parent/'generated_additions';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':10,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'pdf.fonttype':42,'svg.fonttype':'none'})
def save(fig,name):
 for ext in ['png','pdf','svg']:fig.savefig(OUT/f'{name}.{ext}',dpi=400,facecolor='white')
 plt.close(fig)
fig=plt.figure(figsize=(7.2,5.1));ax=fig.add_axes([.03,.03,.94,.94]);ax.set_xlim(0,10);ax.set_ylim(0,7);ax.axis('off')
def box(x,y,w,h,title,body,fc='.96'):
 ax.add_patch(Rectangle((x,y),w,h,facecolor=fc,edgecolor='.4',lw=.7))
 ax.text(x+.14,y+h-.18,title,weight='bold',va='top',fontsize=8.6)
 ax.text(x+.14,y+h-.57,body,va='top',fontsize=8.2,linespacing=1.4)
def arrow(x1,y1,x2,y2):ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=10,color='.3',lw=.9))
ax.text(0,6.85,'a  Define the uncertainty that the experiment can represent',weight='bold',fontsize=10)
box(0,4.95,4.8,1.48,'Observed information','Bitcoin return blocks\nOpening balances and security terms')
box(5.2,4.95,4.8,1.48,'Unresolved conditions','Growth, closure, capacity, valuation,\ncosts, and institutional choices')
arrow(2.4,4.9,3.7,4.42);arrow(7.6,4.9,6.3,4.42)
box(1.25,3.3,7.5,1.08,'One future is a complete external path and set of conditions','Each policy faces the same future; its own decisions change its balances.','.91')
ax.text(5,2.95,'Unspecified events and mechanisms remain outside the explored domain.',ha='center',fontsize=8.3,color='.3')
ax.text(0,2.45,'b  Work backward from unmet objectives to improved financing rules',weight='bold',fontsize=10)
for x,title,body in [(0,'Set objectives','Payments, reserves,\nshareholder outcomes'),(3.4,'Compare policies','Same external futures;\ndifferent transactions'),(6.8,'Explain failures','PRIM regions and\ntransaction diagnostics')]:box(x,1.02,3.2,1.05,title,body,fc='white')
arrow(3.2,1.55,3.4,1.55);arrow(6.6,1.55,6.8,1.55)
ax.plot([8.4,8.4,5,5],[1.0,.55,.55,1.0],color='.3',lw=.9);arrow(5,.75,5,1.0)
ax.text(5,.18,'Revise the rule, then evaluate it on new futures',ha='center',fontsize=8.5)
save(fig,'Figure_1_RDM_framework')
# Geometry of retained inequalities. No simulated observations are invented.
fig=plt.figure(figsize=(7.2,5.2))
def cuboid(ax,bounds):
 (x0,x1),(y0,y1),(z0,z1)=bounds
 v=np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]])
 faces=[[v[i] for i in ids] for ids in [(0,1,2,3),(4,5,6,7),(0,1,5,4),(2,3,7,6),(1,2,6,5),(0,3,7,4)]]
 ax.add_collection3d(Poly3DCollection(faces,facecolor='.35',alpha=.13,edgecolor='.25',linewidth=.7))
for j in range(2):
 ax=fig.add_axes([.01+j*.5,.32,.46,.52],projection='3d');ax.view_init(elev=22,azim=-58)
 ax.tick_params(pad=0,labelsize=6.5);ax.set_box_aspect((1,1,.8))
 ax.xaxis.pane.fill=False;ax.yaxis.pane.fill=False;ax.zaxis.pane.fill=False
 ax.grid(True)
 if j==0:
  ax.set_xlim(0,1.25);ax.set_ylim(0,36);ax.set_zlim(0,2.5)
  cuboid(ax,[(0,.343),(1/30.4375,36),(0,2.258)])
  ax.set_xticks([0,.343,1.25]);ax.set_xticklabels(['0','.343','1.25'])
  ax.set_yticks([0,18,36]);ax.set_zticks([0,2.258]);ax.set_zticklabels(['0','2.258'])
  ax.set_xlabel('Mean capacity scale',labelpad=2);ax.set_ylabel('Closure months',labelpad=2);ax.set_zlabel('Terminal multiplier',labelpad=1)
  fig.text(.04,.93,'a  First funded failure region',weight='bold',fontsize=9.5)
  fig.text(.04,.88,'Additional condition: full holder puts',fontsize=8)
  fig.text(.04,.16,'Capacity ≤ 0.343; closure ≥ 1 day;\nterminal multiplier ≤ 2.258',fontsize=8,linespacing=1.4)
 else:
  ax.set_xlim(-60,220);ax.set_ylim(0,1);ax.set_zlim(0,2.5)
  cuboid(ax,[(-60,8.4),(0,.924),(0,2.234)])
  ax.set_xticks([-60,8.4,220]);ax.set_xticklabels(['−60','8.4','220'])
  ax.set_yticks([0,.924]);ax.set_yticklabels(['0','.924']);ax.set_zticks([0,2.234]);ax.set_zticklabels(['0','2.234'])
  ax.set_xlabel('Bitcoin growth (%/yr)',labelpad=2);ax.set_ylabel('Minimum price / opening',labelpad=2);ax.set_zlabel('Terminal multiplier',labelpad=1)
  fig.text(.54,.93,'b  First nominal value failure region',weight='bold',fontsize=9.5)
  fig.text(.54,.88,'All three displayed conditions apply',fontsize=8)
  fig.text(.54,.16,'Growth ≤ 8.4%/yr; minimum price ≤ 0.924;\nterminal multiplier ≤ 2.234',fontsize=8,linespacing=1.4)
fig.text(.04,.09,'Holdout density 72.8%; coverage 41.0%\nOverall holdout failure share 28.8%',fontsize=7.8,linespacing=1.35)
fig.text(.54,.09,'Holdout density 87.8%; coverage 75.6%\nOverall holdout failure share 59.0%',fontsize=7.8,linespacing=1.35)
fig.text(.5,.025,'Shading depicts fitted inequalities within the displayed bounds, not observed density.',ha='center',fontsize=8,color='.3')
save(fig,'Figure_7_PRIM_regions')
