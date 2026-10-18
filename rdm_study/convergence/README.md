# Sampling convergence supplement

This prospectively specified experiment checks whether the Strategy RDM findings depend on the size or randomization of the Latin hypercube design. It uses the unchanged release 1.1 model, corporate opening, uncertainty ranges, scenario mixture and financing rules. The original study remains intact.

`design_lock.json` records the protocol before new outcomes were generated: code and source identities, dependency versions, nine independent seeds, input and split hashes, eleven policy definitions, six paired contrasts, primary criteria and the escalation rule. Nine input designs are retained, but a retained input alone does not establish that its batch was executed. Completed batch outputs and the final stage summary identify the experiments actually run.

## Completed result

All nine prescribed samples were executed: 51,000 new futures and 561,000 additional policy–future evaluations. Funded shares and paired funded effects pass the convergence criteria at 5,000 and 10,000 futures per replicate. The component interpretation holds in every replication at both long endpoints. At 10,000, the maximum policy-share replicate range is 0.97 percentage points; the maximum paired-effect range is 1.23 points. The maximum adjacent-size mean shift is 0.47 points for policy shares and 0.35 points for paired effects.

Two first-box funding-failure PRIM overlaps remain below 0.60 (0.524 and 0.527). All other primary PRIM checks pass at 10,000, including density, coverage, selected-variable/direction overlap, the funding-box union and the nominal-value regions. The experiment stops as prescribed; it does not retune the boxes or expand the sample to obtain a pass. See `outputs/stage_10000_summary.json`, the complete criterion table, and the accompanying sampling convergence report. `verification.json` records successful sampling, accounting, outcome and holdout-score verification.

## Design

Three independent samples of 2,000 and three of 5,000 futures form the initial comparison. Each future receives all ten report policies plus the sales-only component diagnostic. All four original checkpoints are retained. The primary convergence outcomes are funded shares and six paired funded effects at June 2031 and June 2033. Payments, shareholder targets, conditional returns and near-equal policy rankings provide supporting diagnostics.

The scenario generator uses the original main mixture: 75% stylized paths, 25% historical return-block paths from 2014–2019, and the same dependence, put and authorization branches. Separate samples are not prefixes of one larger Latin hypercube. Drawing new independent Latin hypercubes preserves stratification within each complete design; no pooled-design stratification claim is made.

PRIM is refitted for Reference 100, BPS 100 and Cash and STRC cap, for funded and nominal-value failure at both long endpoints. Each sample retains 75% of its futures for fitting and 25% for validation, with all policies for a future in the same partition. The algorithm, peeling, minimum mass, dimension limits and box selection are unchanged. The original 2,000 main futures provide a common comparison set for the new selected regions; none enters a new fit. The original frozen rules are also evaluated on fresh holdouts. This experiment does not retune policies or select a favorable seed.

## Prespecified decision criteria

At the largest evaluated sample size, each primary funded share and paired funded effect must have a three-replicate range no greater than 2 percentage points. Its mean must differ from the mean at the preceding size by no more than 1 percentage point. The component interpretation must hold in every replicate at both long endpoints.

The primary PRIM checks concern BPS 100 funded and nominal-value failure at June 2031. Both the first box and the union must have common-comparison-set density and coverage ranges no greater than 10 percentage points and adjacent-size mean shifts no greater than 10 points. Every pair of replicate regions must have a Jaccard overlap of at least 0.60. First-box sets of selected variables and inequality directions must have pairwise Jaccard overlap of at least 0.50. Exact cutoffs and their percentile positions are retained as diagnostics, not asserted to be invariant constants. The other policies and June 2033 results remain secondary.

These tolerances are pragmatic choices for this experiment, not universal statistical standards. If any primary criterion fails after the 2,000-versus-5,000 comparison, the protocol requires all three frozen 10,000-future designs. It stops after that comparison even if PRIM remains unstable. Remaining instability must be reported rather than addressed by changing the rule or choosing a favorable result. Three replications do not certify exhaustive coverage or identify real-world event probabilities.

## Reproduce

Follow the parent package's installation and source-checkout instructions. Keep the same pinned numerical environment, and set `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1` before running. The retained protocol and inputs are authoritative; do not invoke `--freeze` over them.

```bash
python rdm_study/convergence/run_convergence.py --sizes 2000 5000 --workers 8
python rdm_study/convergence/evaluate_stage.py --sizes 2000 5000 --analyze --workers 8
```

If `outputs/stage_5000_summary.json` sets `extend_to_10000` to true:

```bash
python rdm_study/convergence/run_convergence.py --sizes 10000 --workers 8
python rdm_study/convergence/evaluate_stage.py --sizes 2000 5000 10000 --analyze --workers 8
```

Use an empty output directory in a separate working copy for a complete rerun. The standard engine runner rejects a CSV without its matching checkpoint and fingerprint; retained delivery CSVs are evidence, not unfinished checkpoints. For a single batch, `run_convergence.py` and `analyze_convergence.py` accept `--tag lhs_2000_r1` (or another frozen tag). `evaluate_stage.py --sizes 2000 5000` recomputes the stage decision from completed per-batch analysis files.

The frozen evaluator's heterogeneous failed-check table contains absent descriptive fields such as policy names for PRIM-only checks. Pandas represents those absent fields as NaN, which its strict JSON writer rejects. `evaluate_stage.py` maps only those absent descriptive fields to JSON null. Numerical criteria, calculations, fits, input designs and the frozen evaluator remain unchanged; nonfinite numerical results still raise an error. The package records this export correction in `serialization_note.json`.

The supplement uses the ordinary model worker for the ten report policies and the already verified sales-only worker for the component contrast. Before freezing, the combined worker exactly reproduced 44 retained checkpoint rows, including outcomes, returns, reserve margins and configuration hashes, for one original future across all eleven policies. Every new engine run checks the ledger prefixes and independently checks stock flows, issuance authority and entitlements.

Output files include individual future-policy-checkpoint records, performance and paired effects, conditional return summaries, PRIM models and complete peeling trajectories, fresh-holdout and common-set scores, region overlaps, selected thresholds, and machine-readable pass/fail criteria. Replication variation measures sensitivity to the exploratory design's randomization. It is not a confidence interval for corporate default or future market outcomes.
