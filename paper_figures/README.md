# Manuscript figures

After unpacking the repository material bundles, `retained/` contains the exact eleven PNG images embedded in manuscript v11. `manuscript_map.json` records their captions and hashes. `paper_tables/` at the repository root contains the 26 displayed tables, including rounding used in the paper.

Run `python scripts/rebuild_paper_figures.py` from the repository root to regenerate all eleven figures in PNG, SVG, and PDF. This uses the preserved figure data and the same plotting logic, with portable paths and a current numbering map. Figure 4 reads the retained transaction ledgers; Figures 1 and 8 are diagrams; the remaining figures use exported manuscript summaries. Rounded summary plots do not replace the full precision simulation records. Fonts and renderer versions can affect regenerated image bytes.

The `base/data/provenance.json` records the earlier manuscript from which those summary plotting inputs were first exported. Later editorial renumbering does not change their numerical values. The final manuscript image set and table exports have their own v11 provenance in `manuscript_map.json`. Original model-report figures remain separately under `rdm_study/figures/`.
