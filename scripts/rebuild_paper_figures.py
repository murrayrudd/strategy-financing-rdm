"""Rebuild all eleven manuscript graphics from the retained plotting data."""
from pathlib import Path
import subprocess, sys, shutil
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'paper_figures'
for script in [P/'base/make_figures.py',P/'make_additions.py',P/'make_transaction_path.py']:
    subprocess.run([sys.executable,str(script)],check=True,cwd=ROOT)
mapping={
 '1':('generated_additions','Figure_1_RDM_framework'),
 '2':('base','Figure_1_Study_setup'),
 '3':('base','Figure_2_Horizon'),
 '4':('generated_path','Figure_4_Transaction_path'),
 '5':('base','Figure_3_Policy_components'),
 '6':('base','Figure_4_Objectives_and_paired_effects'),
 '7':('base','Figure_5_Shareholder_tradeoffs'),
 '8':('generated_additions','Figure_7_PRIM_regions'),
 '9':('base','Figure_S2_Closure_tails'),
 '10':('base','Figure_6_Policy_replications'),
 'B1':('base','Figure_S1_PRIM_stability'),
}
for label,(folder,name) in mapping.items():
    for ext in ['png','pdf','svg']:
        src=P/folder/'figures'/ext/f'{name}.{ext}' if folder=='base' else P/folder/f'{name}.{ext}'
        dst=P/'rebuilt'/ext/f'Figure_{label}.{ext}';dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
print('Rebuilt 11 figures in PNG, PDF, and SVG under paper_figures/rebuilt/.')
