"""Add a checked sampling supplement while preserving every release 1.1 member."""
from pathlib import Path
import hashlib,json,zipfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
WORK=ROOT.parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    baseline=WORK/'release_backup_1_1/Strategy_RDM_Study_Code_and_Results.zip'
    report=WORK/'deliverables/Strategy_RDM_Sampling_Convergence_Report.docx'
    verification=json.loads((HERE/'verification.json').read_text());assert verification['passed']
    qa=json.loads((HERE/'report_quality_check.json').read_text())
    assert qa['all_pages_visually_inspected'] and qa['sha256']==sha(report)
    largest=verification['largest_n'];result=json.loads((HERE/'outputs'/f'stage_{largest}_summary.json').read_text())
    assert largest==10000 or not result['extend_to_10000']
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or 'render_check' in p.parts:continue
        if p.suffix in ['.jsonl','.log','.pyc','.lock'] or p.name=='MANIFEST.json':continue
        files.append(p)
    manifest=dict(supplement='Sampling convergence',base_extension_version='1.1.0',
        baseline_archive_sha256=sha(baseline),protocol_sha256=sha(HERE/'design_lock.json'),
        fresh_futures=result['futures'],additional_policy_evaluations=result['evaluations'],
        largest_sample=largest,criteria=result['criteria'],
        report=dict(filename=report.name,sha256=sha(report)),
        files=[dict(path=str(p.relative_to(HERE)),bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    (HERE/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    target=WORK/'deliverables/Strategy_RDM_Study_Code_and_Results.zip';temporary=target.with_suffix('.tmp.zip')
    with zipfile.ZipFile(baseline) as old,zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as new:
        assert not any(n.startswith('rdm_study/convergence/') for n in old.namelist())
        for info in old.infolist():new.writestr(info,old.read(info.filename))
        for p in files+[HERE/'MANIFEST.json']:new.write(p,'rdm_study/convergence/'+str(p.relative_to(HERE)))
        new.write(report,report.name)
        new.write(HERE/'README.md','SAMPLING_CONVERGENCE_README.md')
    with zipfile.ZipFile(baseline) as old,zipfile.ZipFile(temporary) as new:
        assert len(new.namelist())==len(set(new.namelist())) and new.testzip() is None
        assert all(old.read(n)==new.read(n) for n in old.namelist())
        for f in manifest['files']:assert hashlib.sha256(new.read('rdm_study/convergence/'+f['path'])).hexdigest()==f['sha256']
    temporary.replace(target)
    print(json.dumps(dict(package=str(target),bytes=target.stat().st_size,
                         original_archive_members_unchanged=True,additional_evaluations=result['evaluations']),indent=2))

if __name__=='__main__':main()
