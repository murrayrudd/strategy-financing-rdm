"""Run discovery as frozen batches finish, then apply the locked escalation rule."""
from pathlib import Path
import json, os, subprocess, sys, time
HERE=Path(__file__).resolve().parent

def main():
    batches=json.loads((HERE/'design_lock.json').read_text())['batches']
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    for b in batches:
        if b['n']>5000:continue
        while not (HERE/'outputs'/f"{b['tag']}.csv").exists():time.sleep(2)
        if not (HERE/'outputs'/f"{b['tag']}_prim.json").exists():
            print('Analyze completed batch',b['tag'],flush=True)
            subprocess.run([sys.executable,str(HERE/'analyze_convergence.py'),'--tag',b['tag'],'--workers','2'],env=env,check=True)
    subprocess.run([sys.executable,str(HERE/'evaluate_stage.py'),'--sizes','2000','5000'],env=env,check=True)
    result=json.loads((HERE/'outputs/stage_5000_summary.json').read_text())
    if result['extend_to_10000']:
        print('Locked criteria require all three 10000-future batches.',flush=True)
        for b in batches:
            if b['n']!=10000:continue
            subprocess.run([sys.executable,str(HERE/'run_convergence.py'),'--tag',b['tag'],'--workers','8'],env=env,check=True)
            subprocess.run([sys.executable,str(HERE/'analyze_convergence.py'),'--tag',b['tag'],'--workers','8'],env=env,check=True)
        subprocess.run([sys.executable,str(HERE/'evaluate_stage.py'),'--sizes','2000','5000','10000'],env=env,check=True)
    print('SAMPLING CONVERGENCE PIPELINE COMPLETE',flush=True)

if __name__=='__main__':main()
