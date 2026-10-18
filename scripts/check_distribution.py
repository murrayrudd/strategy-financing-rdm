"""Check the distributed repository files without installing numerical packages."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(2**20):h.update(b)
    return h.hexdigest()
m=json.loads((ROOT/'DISTRIBUTION_MANIFEST.json').read_text());bad=[]
for row in m['repository_files']:
    p=ROOT/row['path']
    if not p.is_file() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:bad.append(row['path'])
if bad:raise SystemExit('Missing or changed distribution files: '+', '.join(bad))
print(json.dumps({'repository_files_checked':len(m['repository_files']),'model_version':m['model_version'],'passed':True}))
