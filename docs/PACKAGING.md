# Packaging and provenance

The source is the retained `Strategy_RDM_Study_Code_and_Results.zip`, model release 1.1.0 with the completed sampling supplement. Source archive SHA-256: `91c4bf1a058ce006201178f65ac651d9a42b7ecebe6ff7fcf15a3dca38dbc812`.

All frozen RDM simulation and analysis programs, locked designs, retained inputs, and completed numerical outputs are distributed byte-for-byte. The two original manifests remain historical records. The current `DISTRIBUTION_MANIFEST.json` and `data/materials_manifest.json` identify the files actually distributed in this upload.

Eight unfinished checkpoint/export intermediates were excluded. They are not completed study evidence or required replay inputs. Original report files are retained under `reports/`; their dates and older figure numbering distinguish them from the current manuscript.

Distribution changes are confined to compression, root documentation, citation metadata, checksummed extraction helpers, a separate numerical-portability verifier, the GitHub verification workflow, and portable paths/current numbering for manuscript plots. The original workflow is retained in `provenance/` after unpacking. No simulated values, policy rules, uncertainty ranges, or fitted PRIM boundaries were changed. The original strict verifier remains intact; the portable verifier does not claim exact regenerated configuration hashes.

The manuscript plot scripts retain the existing plotting logic. Exact v11 images and table exports accompany the scripts. Rendering fonts or versions may change regenerated image bytes without changing the plotted values.

The workflow runs on publication of a release or manual dispatch, after the v1.1.0 result assets exist. No hosted workflow run is claimed by the prepared upload package. Local packaging verification is recorded separately in the upload's validation report.
