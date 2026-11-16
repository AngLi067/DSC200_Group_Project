# Checked run evidence

These small files are snapshots of the successful local full-data run on 2026-11-16. They allow reviewers to inspect results without committing the dataset or large recommendation arrays.

- `metadata.json`: copied from `data/processed/metadata.json`.
- `popularity_metrics.json`: copied from `outputs/popularity/metrics.json`.
- `item_based_cosine_metrics.json`: copied from `outputs/item_based_cosine/metrics.json`.
- `evaluation_summary.json`: copied from `outputs/evaluation_summary.json`.
- `validation_manifest.json`: input/code SHA-256 hashes, dataset cache version, executed commands, test counts, audit observations, and assertions checked against full recommendation arrays.

Re-run the commands in the main README after changing code or data. These committed-source candidates are historical evidence, not files that update automatically. Runtime depends on hardware and load; metric ties may also depend on library behavior. The regression suite uses exact, hand-verifiable cases rather than expecting identical runtime values.
