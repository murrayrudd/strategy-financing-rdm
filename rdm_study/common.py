from pathlib import Path
from datetime import date,timedelta
import sys,json,gzip,hashlib,os,subprocess
from functools import lru_cache

ROOT=Path(__file__).resolve().parent
REPO=Path(os.environ.get('RDM_SOURCE_REPO',ROOT.parent/'source_repo'))
sys.path.insert(0,str(REPO/'research/legacy_engine'))
START=date(2026,6,30)
CORE=date(2031,6,30)
LONG=date(2033,6,30)
TAIL=date(2034,6,30)
CHECKPOINTS=['2027-09-30','2029-06-30',str(CORE),str(LONG)]
TEMPLATE='ba7cfca5a58924a3390db85dcf8d8c98fd568044164231785096d563d5b6bfa3'
SOURCE_COMMIT='ea7aef9f566af346a133712b93357c5b0a0c3c33'
EXTENSION_VERSION='1.1.0'
ENGINE_SCHEMA_VERSION='0.6.0'

def check_source(repo=REPO):
    """Reject a different checkout or changed files actually used by this study."""
    repo=Path(repo)
    try:
        commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True,stderr=subprocess.PIPE).strip()
    except (subprocess.CalledProcessError,FileNotFoundError) as e:
        raise RuntimeError('Set RDM_SOURCE_REPO to the documented frozen git checkout.') from e
    if commit!=SOURCE_COMMIT:
        raise RuntimeError(f'Source commit mismatch: expected {SOURCE_COMMIT}, found {commit}')
    manifest=json.loads((ROOT/'evidence/source_dependencies.json').read_text())
    for rel,expected in manifest['files'].items():
        file=repo/rel
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
            raise RuntimeError(f'Source dependency missing or changed: {rel}. Use a clean checkout and unpack its data.')
    return dict(commit=commit,dependency_sha256=digest(manifest))

@lru_cache(maxsize=1)
def source_identity():
    return check_source()

def source_base():
    source_identity()
    with gzip.open(REPO/'inverse/inputs'/(TEMPLATE+'.json.gz'),'rt') as f:return json.load(f)

def opening_market(point=None):
    """Use the corporate opening; normalize its Bitcoin quote to eight decimals.

    The frozen source stores 58713.99999999999. Currency normalization retains
    the exact 58714 path anchor used in release 1.0 without duplicating a price.
    """
    p=source_base()['initial_point'] if point is None else point
    return dict(price=round(float(p['btc_price_usd']),8),multiple=float(p['multiple']),fx=dict(p['fx_usd_per_unit']))

def write_json(path,value):
    path=Path(path);path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
