# Strategy financing under deep uncertainty

This package implements an RDM extension of Murray A. Rudd's Strategy financing model. It retains the June 30, 2026 opening and August 3, 2026 information cutoff, completes the cash schedules, and evaluates financing rules through June 2031 and June 2033. Separate one-year challenges close both issuance channels after each endpoint. Scenario counts describe the experimental design and are not probabilities.

Release **1.1.0** adds validated experiment restarts, one corporate source for opening market values, executable revised-policy and transaction checks, source dependency verification, and a frozen fresh-future component validation. The inherited `engine_version=0.6.0` identifies the compatible configuration schema; it is not the RDM extension version. Extension and source versions are recorded separately in run manifests.

## Read the results

The companion report explains the findings, assumptions and limits. `outputs/` contains individual future-policy results, performance summaries, matched comparisons, PRIM rules and validation, structural sensitivities and accounting checks. `figures/` contains publication-ready PNG and SVG files. `evidence/` records sources, the policy revision lock and numerical conventions. No original manuscript or source-repository file has been replaced.

## Reproduce

Use Python 3.12. Place this `rdm_study` directory next to a clean clone named `source_repo`, or set `RDM_SOURCE_REPO` to that clone. The source repository is a separate dependency; its original rights and data terms remain in effect.

```bash
git clone https://github.com/murrayrudd/strategy-financing-feasibility source_repo
git -C source_repo checkout ea7aef9f566af346a133712b93357c5b0a0c3c33
python source_repo/scripts/unpack_data.py
python -m venv rdm_env
source rdm_env/bin/activate
python -m pip install -r rdm_study/requirements.txt
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
python rdm_study/verify_release.py
```

The retained inputs reproduce the experimental design without any live data request. Use `futures.py` only to deliberately regenerate the main, challenge and historical designs from their fixed seeds. The source repository supplies frozen Coin Metrics prices and the original corporate opening. Historical prices retain the adjacent Coin Metrics attribution and CC BY-NC 4.0 terms; they are not relicensed here.

The verification command includes a small fresh simulation, an unchanged restart, exact-value comparison with the original exports, and a full ledger replay. The script rejects Python's `-O` mode because the economic verification checks use assertions.

The archive also includes `.github/workflows/rdm-verify.yml`. When the archive contents are installed at a repository root, this workflow runs verification on pushes and pull requests that change the RDM files. A copy is retained under `rdm_study/ci/`. The local release checks do not imply that a hosted GitHub run has already occurred.

The original eight policies must be named explicitly now that two revisions are installed. The retained outputs are evidence from the completed study. To rerun a full experiment, first copy the package into a separate working directory and move that copy's `outputs` directory to `retained_outputs`, then create an empty `outputs` directory. Keep the original delivery intact. Alternatively, use `--output-dir` for individual simulations; the analysis scripts below read the study's `outputs` directory.

```bash
python rdm_study/run_study.py --phase main --workers 8 --policies reference_0 reference_50 reference_100 bps_0 bps_50 bps_100 liquidity_12 liquidity_cap
python rdm_study/analyze.py --phase main --discovery
python rdm_study/run_study.py --phase main --workers 8 --policies anticipatory_12 anticipatory_sale --tag main_revisions
python rdm_study/run_study.py --phase challenge --workers 8
python rdm_study/boundaries.py
python rdm_study/run_study.py --phase boundary --workers 8
python rdm_study/run_study.py --phase stress --workers 8
python rdm_study/run_study.py --phase historical --workers 8
python rdm_study/run_study.py --phase main --mode tail --workers 8 --policies reference_0 reference_50 reference_100 bps_0 bps_50 bps_100 liquidity_12 liquidity_cap --tag main_tail
python rdm_study/run_study.py --phase main --mode tail --workers 8 --policies anticipatory_12 anticipatory_sale --tag revisions_tail
python rdm_study/sensitivity.py --workers 8
python rdm_study/diagnostic_sales.py --workers 4
python rdm_study/component_validation.py --workers 8
python rdm_study/validate_discovery.py
python rdm_study/finalize_analysis.py
python rdm_study/figures.py
python rdm_study/witness.py
```

Runs write resumable JSONL checkpoints before atomically exporting CSV. Each experiment binds its code, source dependencies, installed numerical package versions, full future set, policies, and settings to a manifest. Each checkpoint record carries the experiment fingerprint and its own content checksum. Changed specifications, legacy unversioned checkpoints, duplicate or foreign futures, and incomplete records cause a clear failure. Existing results without a matching manifest are never adopted. Use a new tag or output directory for a changed experiment; no override silently mixes versions. An exclusive lock prevents concurrent writers. After an interrupted process, inspect the recorded host and process before removing a stale lock. Preserve a damaged checkpoint and rerun under a new tag.

The 1.0 CSV outputs remain unchanged evidence. The 1.1 runner deliberately refuses to resume their unversioned JSONL checkpoints. Checkpoint files, transient locks, and rendering intermediates are omitted from the delivery package. Running verification in the intact delivery is supported: its simulations use an isolated temporary output directory.

`common.py` enforces the pinned source commit and hashes the 616 source and frozen-data dependencies listed in `evidence/source_dependencies.json`. Unrelated files are not treated as model dependencies. Bitcoin price, the valuation multiplier, and FX starting values come from the corporate opening configuration. The Bitcoin path anchor rounds the source quote to eight decimal places, preserving the original price paths despite the source's binary representation of $58,714.

For a full auditable ledger of any ordinary or closure result:

```bash
python rdm_study/replay.py main_0003 bps_100 --out example.json.gz
python rdm_study/replay.py main_0003 anticipatory_sale --variant core_stress_closure --out example_tail.json.gz
```

Replay checks the retained configuration hash where a matching CSV exists, independently checks stock flows and entitlements, and writes the complete configuration, atomic ledger, financial states, financing decisions and stop diagnostics. Prefix arithmetic reconciliation is part of every engine run. The report generation script additionally requires `python-docx`; run `python rdm_study/build_report.py` after the analysis and figure steps. The supplied report is already rendered and visually checked. `audit_witnesses.py` independently checks sale-purpose allocations and payment cash on representative full ledgers.

## Model and outcome boundaries

* `payments` means every conditional cash commitment through the checkpoint was met. `funded` additionally requires compliance with the reserve floor at every corporate event since opening. A later recovery cannot erase an earlier reserve breach.
* `nominal_value`, `annual_5pct` and `bitcoin_per_share` additionally require `funded`. Common returns require a defined daily equity mapping throughout the completed path. Stopped paths receive no invented terminal return.
* Common valuation retains the original zero-carry lognormal residual benchmark with 65 percent volatility and a three-year valuation horizon. It is distinct from the five- or seven-year cash simulation. The face-value sensitivity is calibrated to the same opening common-share quote.
* Existing notes repay in cash on the full-put, no-put or partial-put branch. The model does not implement automatic conversion, refinancing, preferred deferral, restructuring or a legal-default determination.
* All preferred distributions are declared in the scenario. STRC costs change with the specified current-rate process; schedules preserve record dates, settlement order, currency calendars and the rate-cut constraint. Future exceptional holiday closures are unknown.
* A one-cent executable common-price floor is an explicit analyst boundary. Sensitivities use one-millionth of a dollar and one dollar. It is not presented as an exchange rule. Additional sensitivities cap event issuance at 2 percent of the model's contemporaneous common market value.
* The new cash rule counts designated reserves once. It values known future service at current rates and FX and protects against the earliest possible future holder put. It never observes a future price, realized closure duration or future put election.
* `anticipatory_12` raises common capital in advance to meet that cash target, subject to current capacity and remaining authorization. `anticipatory_sale` also permits cumulative general-purpose Bitcoin sales up to $6,753,703,000 gross, the opening debt principal amount. Both cap new STRC stated principal at half the opening STRC amount.
* The first unsupported payment stops the ledger. The model can continue after a reserve-only breach, but the strict funded target remains failed. This distinguishes a policy constraint from immediate inability to pay.

## Scenario discovery

PRIM uses continuous exogenous trajectory summaries, separately by policy and target. It fits on 1,500 futures, keeps 500 internal design cases aside, limits selected boxes to four restricted dimensions, and seeks 90 percent density with 5 percent minimum mass. Results that do not reach the density target remain labeled as such. Unrestricted dimensions do not acquire artificial training-range cutoffs during transfer.

The 512 reserved challenge futures change both the historical block pool and the stylized recovery generator. Policies and rules were locked before these outcomes were run. Complete historical paths overlap the data pools and are descriptive checks, not independent validation. Boundary perturbations are local diagnostics, not independent evidence. CART is a shallow diagnostic; QCA and latent class analysis are outside this study.

A separate post-discovery component diagnostic tests the cash-and-STRC-cap rule with general sale authority but without advance funding on all 2,000 main futures. It isolates the cash-timing and permission components. It does not retune the primary policies or claim reserved-set validation. Its results are reported separately.

Release 1.1 adds 512 new futures for all four component combinations. The design, seed, model code, policy definitions, outcomes, and paired comparisons were frozen in `evidence/component_validation_lock.json` before outcomes were generated. The fresh draws reuse the reserved design's historical pool and plateau generator, so they test transfer to new futures within that design, not to a new historical data source. The supplied input file is authoritative; do not rerun `--freeze` over it. The runner verifies the frozen definition before executing. A different software environment may require a new, explicitly versioned validation study rather than resuming the locked experiment.

## Provenance and rights

`engine.py` derives from the source repository's settlement engine 0.6.0. The extension adds cash coverage and preferred caps, advances financing, completes long schedules and accelerates equivalent accrual and journal operations. The original engine remains unchanged. Original economic states and retained result hashes are checked separately; the derivative is not represented as the unmodified original engine. This research package makes no new blanket license grant over the original code or third-party material.
