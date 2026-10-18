"""Restore frozen materials, validating hashes and protecting changed files."""
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
import argparse, hashlib, json, os, tempfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while b:=f.read(2**20):h.update(b)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--include',choices=['core','main','all'],default='core')
    p.add_argument('--assets-dir',type=Path,default=ROOT/'release_assets')
    a=p.parse_args();manifest=json.loads((ROOT/'data/materials_manifest.json').read_text())
    allowed={'core'} if a.include=='core' else {'core','main'} if a.include=='main' else {'core','main','convergence'}
    selected=[b for b in manifest['bundles'] if b['group'] in allowed]
    # Validate all requested archives before changing the destination tree.
    for b in selected:
        src=ROOT/b['path'] if b['group']=='core' else a.assets_dir/b['path']
        if not src.is_file():raise FileNotFoundError(f'Missing {src.name}. Download the matching v1.1.0 release attachment into {a.assets_dir}.')
        if src.stat().st_size!=b['bytes'] or sha(src)!=b['sha256']:raise ValueError(f'Archive checksum mismatch: {src.name}')
    count=written=0
    for b in selected:
        src=ROOT/b['path'] if b['group']=='core' else a.assets_dir/b['path']
        expected={m['path']:m for m in b['members']}
        with ZipFile(src) as z:
            if len(z.namelist())!=len(expected) or set(z.namelist())!=set(expected):raise ValueError('Archive member list changed')
            for info in z.infolist():
                rel=PurePosixPath(info.filename);dest=ROOT.joinpath(*rel.parts);m=expected[info.filename]
                if rel.is_absolute() or '..' in rel.parts or not dest.resolve().is_relative_to(ROOT):raise ValueError('Unsafe archive path')
                if (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive symlink rejected')
                if info.file_size!=m['bytes']:raise ValueError('Member length differs')
                if dest.exists():
                    if not dest.is_file() or sha(dest)!=m['sha256']:raise ValueError(f'Changed retained file: {info.filename}. Use a fresh working copy.')
                    count+=1;continue
                dest.parent.mkdir(parents=True,exist_ok=True)
                fd,tmp=tempfile.mkstemp(prefix='rdm_extract_',dir=dest.parent)
                try:
                    h=hashlib.sha256();size=0
                    with os.fdopen(fd,'wb') as out,z.open(info) as inp:
                        while block:=inp.read(2**20):out.write(block);h.update(block);size+=len(block)
                    if size!=m['bytes'] or h.hexdigest()!=m['sha256']:raise ValueError(f'Member checksum mismatch: {info.filename}')
                    os.replace(tmp,dest);written+=1;count+=1
                finally:
                    if os.path.exists(tmp):os.unlink(tmp)
    print(json.dumps({'checked_members':count,'files_restored':written,'included':a.include}))
if __name__=='__main__':main()
