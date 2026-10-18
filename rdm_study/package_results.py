"""Freeze a complete, checked package; excludes transient run checkpoints."""
import json,hashlib,zipfile,shutil,argparse
from pathlib import Path
from common import ROOT,REPO,write_json,EXTENSION_VERSION,SOURCE_COMMIT
from execution import simulation_identity
from component_validation import check_lock

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--candidate',action='store_true');parser.add_argument('--out',type=Path);args=parser.parse_args()
 inventory=json.loads((ROOT/'outputs/experiment_inventory.json').read_text())
 assert inventory['all_prefixes_reconciled']
 assert inventory['total_evaluations']==119212
 assert json.loads((ROOT/'outputs/verification.json').read_text())['passed']
 verification=json.loads((ROOT/'outputs/release_verification.json').read_text())
 assert verification['passed'] and verification['simulation']==simulation_identity()
 check_lock()
 lock=json.loads((ROOT/'evidence/adaptation_lock.json').read_text())
 for key,name in [('discovery_sha256','outputs/prim_models.json'),('challenge_input_sha256','inputs/futures_challenge.json')]:
  assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==lock[key]
 for name in ['LICENSE.md','THIRD_PARTY_NOTICES.md']:
  shutil.copy2(REPO/name,ROOT/'evidence'/('SOURCE_'+name))
 report=ROOT.parent/'deliverables/Strategy_RDM_Results_Report.docx';assert report.is_file()
 if not args.candidate:
  clean=json.loads((ROOT/'evidence/clean_install_verification.json').read_text())
  assert clean['passed'] and clean['report_parts_match'] and clean['isolated_environment']
  for name,expected in clean['verified_code_sha256'].items():
   assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected
  qa=json.loads((ROOT/'evidence/report_quality_check.json').read_text())
  assert qa['all_pages_visually_inspected'] and qa['sha256']==hashlib.sha256(report.read_bytes()).hexdigest()
 files=[]
 for p in sorted(ROOT.rglob('*')):
  if not p.is_file() or '__pycache__' in p.parts or 'render_check' in p.parts:continue
  if p.suffix in ['.log','.jsonl','.pyc'] or p.name=='MANIFEST.json':continue
  files.append(p)
 manifest=dict(study='Strategy RDM extension',extension_version=EXTENSION_VERSION,source_commit=SOURCE_COMMIT,date='2026-10-11',inventory=inventory,report=dict(filename=report.name,sha256=hashlib.sha256(report.read_bytes()).hexdigest()),files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
 write_json(ROOT/'MANIFEST.json',manifest)
 target=args.out or ROOT.parent/'deliverables/Strategy_RDM_Study_Code_and_Results.zip'
 with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
  for p in files+[ROOT/'MANIFEST.json']:archive.write(p,'rdm_study/'+str(p.relative_to(ROOT)))
  archive.write(report,report.name)
  archive.write(ROOT/'ci/rdm-verify.yml','.github/workflows/rdm-verify.yml')
 with zipfile.ZipFile(target) as archive:
  assert archive.testzip() is None
  for f in manifest['files']:
   assert hashlib.sha256(archive.read('rdm_study/'+f['path'])).hexdigest()==f['sha256']
 print(json.dumps(dict(package=str(target),bytes=target.stat().st_size,files=len(files)+3,evaluations=inventory['total_evaluations'],extension_version=EXTENSION_VERSION,candidate=args.candidate),indent=2))

if __name__=='__main__':main()
