"""Experiment fingerprints and exclusive, validated resumable checkpoints."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import socket
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
from common import ROOT, EXTENSION_VERSION, ENGINE_SCHEMA_VERSION, digest, source_identity, write_json

SIMULATION_FILES = ['common.py', 'engine.py', 'terms.py', 'futures.py', 'model.py',
                    'metrics.py', 'execution.py', 'run_study.py', 'sensitivity.py',
                    'diagnostic_sales.py', 'component_validation.py']


def simulation_identity():
    return {
        'extension_version': EXTENSION_VERSION,
        'inherited_engine_schema_version': ENGINE_SCHEMA_VERSION,
        'source': source_identity(),
        'python': platform.python_version(),
        'dependencies': {name: importlib.metadata.version(name) for name in
                         ['numpy', 'pandas', 'scipy', 'holidays', 'python-dateutil']},
        'code': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                 for name in SIMULATION_FILES if (ROOT/name).exists()},
    }


def experiment_spec(futures, settings):
    ids = [f['future_id'] for f in futures]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('An experiment requires nonempty, unique future IDs.')
    return {'format_version': 1, 'simulation': simulation_identity(),
            'futures_sha256': digest(futures), 'future_ids': ids, 'settings': settings}


def read_checkpoint(path, fingerprint, allowed_ids):
    records = []
    seen = set()
    if not path.exists():
        return records
    with path.open() as stream:
        for number, line in enumerate(stream, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f'Incomplete or damaged checkpoint at line {number}; preserve it and use a new run tag.') from exc
            ident = record.get('future_id')
            if record.get('experiment_sha256') != fingerprint:
                raise RuntimeError(f'Checkpoint fingerprint mismatch at line {number}.')
            if ident not in allowed_ids or ident in seen:
                raise RuntimeError(f'Unknown or duplicate checkpoint future: {ident}')
            if record.get('record_sha256') != digest({k: v for k, v in record.items() if k != 'record_sha256'}):
                raise RuntimeError(f'Checkpoint content checksum mismatch: {ident}')
            if not record.get('rows') or any(r.get('future_id') != ident for r in record['rows']):
                raise RuntimeError(f'Checkpoint rows do not match their future: {ident}')
            seen.add(ident)
            records.append(record)
    return records


def open_experiment(directory, tag, spec):
    """Validate before appending; never adopt unversioned legacy checkpoints."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', tag):
        raise ValueError('Run tags may contain letters, digits, underscores, periods, and hyphens.')
    manifest = directory/(tag+'_experiment.json')
    checkpoint = directory/(tag+'.jsonl')
    fingerprint = digest(spec)
    if manifest.exists():
        stored = json.loads(manifest.read_text())
        if stored != {'experiment_sha256': fingerprint, 'specification': spec}:
            raise RuntimeError('Experiment changed. Code, inputs, policies, settings, source, and environment must match to resume. Use a new tag or output directory.')
    else:
        if checkpoint.exists() or (directory/(tag+'.csv')).exists():
            raise RuntimeError('Existing results have no matching experiment manifest. Preserve them and use a new tag or output directory.')
        temporary = manifest.with_suffix('.tmp')
        write_json(temporary, {'experiment_sha256': fingerprint, 'specification': spec})
        temporary.replace(manifest)
    records = read_checkpoint(checkpoint, fingerprint, set(spec['future_ids']))
    return checkpoint, fingerprint, records


def run_batch(futures, settings, worker, task_builder, *, directory, tag, workers=8):
    """One writer per experiment; completed records bind to the full specification."""
    directory = Path(directory)
    if workers < 1:
        raise ValueError('workers must be positive')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', tag):
        raise ValueError('Invalid run tag')
    spec = experiment_spec(futures, settings)
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory/(tag+'.lock')
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(f'Run is locked: {lock}. Confirm its recorded process is stopped before removing a stale lock.') from exc
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump({'pid': os.getpid(), 'host': socket.gethostname()}, stream)
        checkpoint, fingerprint, records = open_experiment(directory, tag, spec)
        done = {r['future_id'] for r in records}
        pending = [f for f in futures if f['future_id'] not in done]
        started = time.time()
        with checkpoint.open('a') as stream, ProcessPoolExecutor(max_workers=workers) as pool:
            jobs = {pool.submit(worker, task_builder(f)): f['future_id'] for f in pending}
            for n, job in enumerate(as_completed(jobs), 1):
                record = job.result()
                if record.get('future_id') != jobs[job] or not record.get('rows'):
                    raise RuntimeError('Worker returned the wrong future or no results.')
                record['experiment_sha256'] = fingerprint
                record['record_sha256'] = digest(record)
                stream.write(json.dumps(record, allow_nan=False)+'\n')
                stream.flush()
                os.fsync(stream.fileno())
                records.append(record)
                if n % 25 == 0 or n == len(pending):
                    print(f'{tag}: {len(done)+n}/{len(futures)} futures, {time.time()-started:.1f}s', flush=True)
        rows = [row for record in records for row in record['rows']]
        data = pd.DataFrame(rows).sort_values(['future_id', 'policy', 'horizon', 'variant'])
        if data.duplicated(['future_id', 'policy', 'horizon', 'variant']).any():
            raise RuntimeError('Duplicate result keys; results were not exported.')
        temporary = directory/(tag+'.csv.tmp')
        data.to_csv(temporary, index=False)
        temporary.replace(directory/(tag+'.csv'))
        write_json(directory/(tag+'_run.json'), dict(experiment_sha256=fingerprint,
                   futures=len(futures), new_futures=len(pending), records=len(data),
                   seconds=time.time()-started, extension_version=EXTENSION_VERSION))
        print('COMPLETE', tag, len(data), flush=True)
        return data
    finally:
        lock.unlink(missing_ok=True)
