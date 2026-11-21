# Checked run evidence

These files record run results without including the dataset or large recommendation arrays. The original snapshots below come from the successful local full-data run on 2026-11-16.

- `metadata.json`: copied from `data/processed/metadata.json`.
- `popularity_metrics.json`: copied from `outputs/popularity/metrics.json`.
- `item_based_cosine_metrics.json`: copied from `outputs/item_based_cosine/metrics.json`.
- `evaluation_summary.json`: copied from `outputs/evaluation_summary.json`.
- `validation_manifest.json`: input/code SHA-256 hashes, dataset cache version, executed commands, test counts, audit observations, and assertions checked against full recommendation arrays.

The 2026-11-18 integration adds `data_quality_2026-11-18.json`, a complete audit snapshot containing source fingerprints, 17 validation checks, bounded warning examples, descriptive profiles, and measured audit-stage times. The four raw hashes match the original manifest. `integration_2026-11-18.json` records the updated source hashes and integration verification results. The original November 16 snapshots remain unchanged.

Re-run the commands in the main README after changing code or data. These snapshots record past runs and do not update automatically. Runtime depends on hardware and load; metric ties may also depend on library behavior. The regression suite uses exact, hand-verifiable cases rather than expecting identical runtime values.
