# Reproducing the study

Run commands from the root of this repository. Use a clean working copy and Python 3.12.14. The frozen design checks Python and the numerical packages that determine the simulation and PRIM calculations. A different environment may fail the identity checks; do not bypass them or overwrite the locked design.

## 1. Restore the retained materials

The two ZIPs in `data/` are tracked repository files. Run:

```bash
python scripts/check_distribution.py
python scripts/unpack_materials.py
```

Download `strategy-rdm-main-results-v1.1.0.zip` and `strategy-rdm-convergence-results-v1.1.0.zip` from this repository's v1.1.0 release into a folder named `release_assets` at the repository root. Leave the ZIPs compressed and run:

```bash
python scripts/unpack_materials.py --include all
```

The unpacker checks archive and member hashes, rejects unsafe paths, and refuses to replace an existing file whose contents differ. Use a fresh copy if a previous analysis has changed a retained output. The large result ZIPs are release attachments, not ordinary Git files.

## 2. Install the pinned upstream source

```bash
git clone https://github.com/murrayrudd/strategy-financing-feasibility source_repo
git -C source_repo checkout ea7aef9f566af346a133712b93357c5b0a0c3c33
python source_repo/scripts/unpack_data.py
```

The default `source_repo/` location works without an environment variable. If the clone is elsewhere, set `RDM_SOURCE_REPO` to its absolute path. The code checks the exact commit and 616 source/data dependency hashes. No live market-data request is needed after this installation.

## 3. Install Python dependencies

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r rdm_study/requirements.txt
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
.\.venv\Scripts\python.exe scripts/verify_portable.py
.\.venv\Scripts\python.exe rdm_study/convergence/verify_convergence.py --largest 10000
```

On macOS or Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r rdm_study/requirements.txt
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
.venv/bin/python scripts/verify_portable.py
.venv/bin/python rdm_study/convergence/verify_convergence.py --largest 10000
```

Install Python 3.12.14 specifically. The Windows launcher example selects an installed 3.12 interpreter; check its patch version with `py -3.12 --version`. Use the environment's Python for all later commands. Do not run with `-O`, because verification assertions must remain active.

The first verifier checks source identity, engine and policy behavior, transaction witnesses, restart behavior, numerical parity of 64 retained checkpoint rows, and two complete retained-ledger replays. The second checks all nine replication batches, input stratification, outcome counts, paired contrasts, and fresh-holdout PRIM scores. A successful verifier does not mean every scientific convergence criterion passed: the two reported PRIM membership failures remain part of the results. Verification refreshes its verification JSON files; preserve the original distribution separately if exact retained bytes are needed later.

### Numerical portability

The original `rdm_study/verify_release.py` and `rdm_study/replay.py` are preserved unchanged. They require exact numerical values and hashes of newly generated configurations. The packaging environment reproduced the outcomes within numerical round-off but did not reproduce those configuration hashes. Do not describe the portable check as exact hash replication or bypass the model's restart identity checks.

`scripts/verify_portable.py` is a separate distribution check. It requires exact record keys, dates, categorical outcomes, integers, booleans, source hashes, and no-op restart bytes. Continuous checkpoint values use relative tolerance 1e-12 and absolute tolerance 1e-10. It compares two regenerated witness configurations to the retained full configurations at relative tolerance 1e-14 and absolute tolerance 1e-12. It then replays the retained configurations, requires their original hashes, and compares the complete ledgers at relative tolerance 1e-11 and absolute tolerance 0.002 for floating values. Dictionary keys, list order, and discrete fields remain exact. The report lists all configuration hash mismatches and numerical differences. See the upload validation report for the observed differences.

For the stricter historical check, run `python rdm_study/verify_release.py`. A failure caused only by numerical round-off is distinct from a failed portable verification; investigate any difference outside the stated tolerances. No simulation program or frozen result was modified to make a check pass.

## 4. Reproduce outputs without rerunning all futures

```bash
python scripts/rebuild_paper_figures.py
python rdm_study/convergence/evaluate_stage.py --sizes 2000 5000 10000
```

The first command writes all eleven manuscript figures to `paper_figures/rebuilt/` in PNG, PDF, and SVG. The second recomputes the final convergence criteria from retained per-batch analysis records. It does not refit PRIM unless `--analyze` is supplied. See `paper_figures/README.md` for the distinction between exact retained images and regenerated output.

The original technical report can be rebuilt with `python rdm_study/build_report.py`. It predates the final manuscript layout and figure numbering; it is supporting analysis, not the current paper. `rdm_study/convergence/build_convergence_report.py` rebuilds its separate technical supplement.

## 5. Run new simulations or repeat the full study

The detailed commands are in `rdm_study/README.md` and `rdm_study/convergence/README.md`. Use a separate working copy. Move retained output directories aside and create empty output directories for reruns; keep the authoritative input designs and split files. The guarded runner rejects retained CSVs without matching live checkpoints because completed evidence is not an unfinished run.

The source programs preserve the original study sequence: eight initial policies, two revisions, the sales-only diagnostic, reserved challenge, fresh component test, closure continuations, structural sensitivities, and sampling replications. Do not replace that sequence with eleven policies in every original experiment. Do not run `--freeze` over existing protocol files. Full simulations are substantially more expensive than verification or figure rebuilding.
