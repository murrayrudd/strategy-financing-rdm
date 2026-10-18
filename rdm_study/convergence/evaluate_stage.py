"""Export the frozen analysis, mapping absent descriptive metadata to JSON null.

The frozen evaluator successfully computes its criteria but its heterogeneous
failed-check table acquires pandas NaNs in inapplicable metadata columns. The
strict JSON writer rejects those NaNs. This adapter changes only serialization
of absent descriptive metadata; nonfinite numerical results still raise.
"""
import argparse, math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import write_json
import analyze_convergence

METADATA={'horizon','policy','comparator','outcome','kind','a','b'}

def clean(value,key=None):
    if isinstance(value,dict):return {k:clean(v,k) for k,v in value.items()}
    if isinstance(value,list):return [clean(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value):
        if key in METADATA:return None
        raise ValueError(f'Nonfinite numerical result in {key}')
    return value

def export(path,value):write_json(path,clean(value))

def main():
    p=argparse.ArgumentParser();p.add_argument('--sizes',nargs='+',type=int,required=True);p.add_argument('--analyze',action='store_true');p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    analyze_convergence.write_json=export
    if a.analyze:
        lock=analyze_convergence.check_lock()
        for batch in lock['batches']:
            if batch['n'] in a.sizes:analyze_convergence.analyze_batch(batch,a.workers)
    analyze_convergence.evaluate(a.sizes)

if __name__=='__main__':main()
