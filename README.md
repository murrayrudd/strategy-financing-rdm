# Strategy financing under deep uncertainty

[![Verification](https://github.com/murrayrudd/strategy-financing-rdm/actions/workflows/rdm-verify.yml/badge.svg)](https://github.com/murrayrudd/strategy-financing-rdm/actions/workflows/rdm-verify.yml)

Code and replication materials for Murray A. Rudd's study of financing resilience and common shareholder outcomes in Strategy, a Bitcoin treasury company.

The study compares eleven financing policies across the same external futures. It follows payments, reserves, issuance, Bitcoin holdings, and common shareholder exposure from June 2026 through June 2031 and June 2033, with separate one-year issuance-closure challenges. Robust decision making and PRIM scenario discovery connect failure conditions to policy revisions and independent tests. Success shares describe the explored domain; they are not forecasts of corporate default or investment returns.

**Model version:** 1.1.0, frozen October 11, 2026. This upload package adds documentation, portable figure paths, and compressed distribution bundles without changing the simulation programs, policy definitions, locked inputs, or retained numerical results. The working paper is available on SSRN: [doi:10.2139/ssrn.7632598](https://doi.org/10.2139/ssrn.7632598).

## Main findings

- At June 2031, the main 2,000-future design gives funded success of 68.7% for BPS 100 and 87.1% for advance funding plus broader sale permission. Funded success requires every payment and reserve compliance throughout the path.
- Advance common funding mainly protects reserves. Broader sale permission mainly prevents payment stops. Their combination does not preserve Bitcoin per share or eliminate dilution and interim losses.
- Nine independent Latin hypercube replications add 51,000 futures and 561,000 policy-future evaluations. At 10,000 futures per sample, funded shares and paired effects meet the prespecified convergence tolerances. Two first-region PRIM membership comparisons remain below the required overlap threshold.

## Start here

Use **Python 3.12.14** and Git. From this repository's root, unpack the two included material bundles:

```bash
python scripts/check_distribution.py
python scripts/unpack_materials.py
```

This restores the frozen inputs, provenance, summary results, PRIM records, publication graphics, and displayed manuscript tables. It does not run the simulation. To reproduce figures alone:

```bash
python -m pip install -r rdm_study/requirements.txt
python scripts/rebuild_paper_figures.py
```

For full verification, download both result ZIPs attached to [release **v1.1.0**](https://github.com/murrayrudd/strategy-financing-rdm/releases/tag/v1.1.0) into `release_assets/` and run:

```bash
python scripts/unpack_materials.py --include all
```

Then follow [installation and replication instructions](docs/REPRODUCING.md). They include the exact pinned commit of the earlier [Strategy financing-feasibility repository](https://github.com/murrayrudd/strategy-financing-feasibility), which supplies the original engine, corporate opening, and historical data. The RDM project is a separate study.

## Contents

| Path | Purpose |
|---|---|
| `rdm_study/` | Unchanged frozen model and analysis programs |
| `rdm_study/convergence/` | Locked sampling protocol and replication programs |
| `data/` | Two compressed input/summary bundles and their checksums |
| `paper_figures/` | Portable plotting scripts; exact manuscript graphics appear after unpacking |
| `paper_tables/` | All 26 displayed manuscript tables, restored by unpacking |
| `docs/REPRODUCING.md` | Installation, verification, rerun, and figure commands |
| `docs/MANUSCRIPT_MAP.md` | Policy names and correspondence between results and the manuscript |
| `DISTRIBUTION_MANIFEST.json` | File inventory and integrity checks for this upload package |

The full result CSVs are release attachments because some exceed GitHub's repository file-size limit. They retain the original filenames and uncompressed bytes when unpacked. The included bundles support inspection and figure reproduction without downloading those larger records.

## Research basis

**Rudd, M. A. (2026).** *Strategy financing under deep uncertainty*. SSRN working paper.
[https://doi.org/10.2139/ssrn.7632598](https://doi.org/10.2139/ssrn.7632598).

This RDM study extends the corporate financing implementation associated with
[Financing feasibility and shareholder outcomes in a Bitcoin treasury company:
historical validation and conditional stress testing of Strategy](https://doi.org/10.2139/ssrn.7593458).
The [earlier replication repository](https://github.com/murrayrudd/strategy-financing-feasibility)
is a pinned dependency; installation instructions identify the required commit.

## Citation

If you use this code or its results in research, please cite the accompanying
paper and identify model version 1.1.0 and the repository commit used:

```bibtex
@unpublished{Rudd2026StrategyRDM,
  author = {Rudd, Murray A.},
  title = {Strategy financing under deep uncertainty},
  year = {2026},
  doi = {10.2139/ssrn.7632598},
  url = {https://doi.org/10.2139/ssrn.7632598},
  note = {SSRN working paper}
}
```

[CITATION.cff](CITATION.cff) supplies machine-readable software metadata and the
preferred paper citation through GitHub's **Cite this repository** option.
The [versioned code and results release](https://github.com/murrayrudd/strategy-financing-rdm/releases/tag/v1.1.0)
provides a fixed reference for replication. The software has no separate DOI.

## License

Original project code and associated software documentation are available under
the [MIT License](LICENSE.md). See [license scope](LICENSE_SCOPE.md) for coverage
of earlier revisions and the distinction between software and data. Coin Metrics
data retain CC BY-NC 4.0 terms; other third-party material retains its source terms.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Author

**Murray A. Rudd, Ph.D.** — Institutional economist and policy researcher

- ORCID: [0000-0001-9533-5070](https://orcid.org/0000-0001-9533-5070)
- SSRN: [Author profile](https://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id=5958022)
- Google Scholar: [Profile](https://scholar.google.co.uk/citations?hl=en&user=84qbofEAAAAJ)
