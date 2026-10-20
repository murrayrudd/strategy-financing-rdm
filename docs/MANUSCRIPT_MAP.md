# Manuscript and code correspondence

The manuscript reference is v11, dated October 18, 2026. The manuscript is available as an [SSRN working paper](https://doi.org/10.2139/ssrn.7632598), DOI `10.2139/ssrn.7632598`. Displayed table values and exact embedded figure images are retained after unpacking; raw outputs remain separate and preserve full precision.

| Paper policy | Code key |
|---|---|
| P1 Reference 0 | `reference_0` |
| P2 Reference 50 | `reference_50` |
| P3 Reference 100 | `reference_100` |
| P4 BPS 0 | `bps_0` |
| P5 BPS 50 | `bps_50` |
| P6 BPS 100 | `bps_100` |
| P7 Cash protection | `liquidity_12` |
| P8 Cash and STRC cap | `liquidity_cap` |
| P9 Advance cash funding | `anticipatory_12` |
| P10 Advance funding and sales | `anticipatory_sale` |
| P11 Sales permission only | `sales_only` |

P11 is a separate component diagnostic in the original experiment and participates in all nine convergence replications. It was not tested in every original stress/sensitivity branch. Denominators and policy scope therefore follow the relevant experiment.

| Manuscript content | Principal retained source |
|---|---|
| Table 4; Figure 3 | `outputs/all_main_performance.csv`, `outputs/component_diagnostic_performance.csv` |
| Tables 5–6; Figures 5–6 | Main and component performance/paired outputs; `outputs/fresh_component_effects.csv` |
| Figure 4 | `outputs/witness_liquidity_cap.json.gz`, `outputs/witness_anticipatory_12.json.gz`, `outputs/witness_summary.json` |
| Figure 7; Table B3 | `outputs/common_domain_economics.csv` |
| Table 7; Figure 8 | `outputs/prim_models.json`, `outputs/prim_external_validation.csv` |
| Table 8 | Challenge and fresh-component performance files |
| Figure 9; Table B4 | `outputs/tail_retention.csv` |
| Table 9; Figure 10 | `convergence/outputs/stage_10000_performance.csv` (10,000-future rows) |
| Figure B1; Tables B6–B7 | PRIM sensitivity and convergence score/overlap/threshold files |

Paths in the second column are relative to `rdm_study/`. `paper_figures/manuscript_map.json` gives all figure captions and table export paths. The plotting sources retain some older filenames; `scripts/rebuild_paper_figures.py` maps them to the current figure numbers.

## Interpretation of the records

The original design has 2,000 futures. The convergence supplement adds nine independent designs, three each at 2,000, 5,000, and 10,000 futures. Those are 51,000 new futures and 561,000 policy-future evaluations, recorded at four checkpoints. Checkpoints and repeated policies are not additional independent futures. Results averaged over the three 10,000-future samples are distinct from the original 2,000-future findings.

`payments` records schedule completion; `funded` also requires continuous reserve compliance. The shareholder success targets include `funded`. Conditional return and financing summaries use common completed-path subsets; they do not use every original future. The manuscript tables and captions specify their denominators.
