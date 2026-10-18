# Strategy financing under deep uncertainty

Code and replication materials for Murray A. Rudd's study of financing resilience and common shareholder outcomes in Strategy, a Bitcoin treasury company.

The study compares eleven financing policies across the same external futures. It follows payments, reserves, issuance, Bitcoin holdings, and common shareholder exposure from June 2026 through June 2031 and June 2033, with separate one-year issuance-closure challenges. Robust decision making and PRIM scenario discovery connect failure conditions to policy revisions and independent tests. Success shares describe the explored domain; they are not forecasts of corporate default or investment returns.

**Model version:** 1.1.0, frozen October 11, 2026. This upload package adds documentation, portable figure paths, and compressed distribution bundles without changing the simulation programs, policy definitions, locked inputs, or retained numerical results. The paper is a working manuscript; its public link and DOI will be added when available.

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

For full verification, download both result ZIPs attached to release **v1.1.0** into `release_assets/` and run:

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

## Citation and rights

Please cite Murray A. Rudd, *Strategy financing under deep uncertainty* (2026), and identify model version 1.1.0 plus the repository commit used. `CITATION.cff` supplies citation metadata without inventing a publication DOI or repository address.

No general open-source license has been selected. See [LICENSE.md](LICENSE.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Historical Coin Metrics data retain their source attribution and CC BY-NC 4.0 terms; upstream code and other source material retain their existing rights.
