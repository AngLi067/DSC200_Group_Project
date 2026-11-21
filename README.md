# Availability-Aware E-Commerce Recommendation

This project uses the Retailrocket e-commerce dataset to compare popularity and item-based recommendations, then measures how filtering products with a known unavailable state affects recommendation quality. The data has historical availability states, not physical inventory quantities.

## Project documentation

- [Specification](docs/project_spec.md): requirements, data schema, architecture, and test cases.
- [Implementation status](docs/project_update.md#implementation-status): progress on each requirement and remaining validation work.
- [Verification results](docs/project_update.md#verification-evidence): automated test outcomes and full-data pipeline checks.
- [Specification changes](docs/project_update.md#specification-clarifications-identified-during-implementation): candidate eligibility, padding, data acquisition, and evaluation rules clarified during development.
- [Team contributions](docs/project_update.md#team-contributions) and development reflections: [Ang Li](docs/project_update.md#personal-reflection-ang-li), [Wuxuan Wang](docs/project_update.md#personal-reflection-wuxuan-wang), and [Abby Li](docs/project_update.md#personal-reflection-abby-li).
- [Run evidence](docs/results/README.md): full-data metrics, audit results, and source hashes.
- [Data-quality checks](docs/data_quality.md): validation rules, report structure, warnings, and limitations.

## Implementation progress

FR-1 through FR-3 are implemented: the pipeline prepares the data, runs both models, and saves raw and filtered rankings with evaluation results. NFR-1 and NFR-2 are covered by temporal-isolation, mapping, filtering, and invalid-input checks. For NFR-3, the documented workflow, pinned dependencies, sparse storage, and offline tests are in place. A fresh installation on another machine remains unverified.

All 31 automated tests passed on November 21, including U-1 through U-3 and F-1 through F-3; none failed. The November 18 full-data run completed preparation and both models, with zero known-unavailable items in the filtered rankings. All 14 file hashes in its [integration record](docs/results/integration_2026-11-18.json) still matched during the November 21 check. That check reran the automated tests, not the full-data pipeline.

Implementation exposed rules that needed to be explicit in the spec. Candidates must have training interactions, even though the ID mappings also contain future-only targets. Short rankings need unique IDs and `-1` padding. Unknown availability remains eligible, while unavailable future targets stay in the recall denominator. We added these rules to the spec; defining them before implementation would have made the pipeline interfaces and expected test results clearer.

## Quick offline test run

From the repository root, install dependencies if needed, then run the suite:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m unittest discover -s tests -v
```

Dependency installation may require network access. The tests themselves use synthetic fixtures and require no network, Kaggle account, or dataset download. On November 21, 2026, all 31 tests passed with no failures or errors, including the six cases defined in the specification below. This check used the existing local environment.

| Spec case | Test file | Exact method | Result |
| --- | --- | --- | --- |
| U-1 | [test_recommendation_models.py](tests/test_recommendation_models.py) | `AvailabilityTests.test_asof_join_uses_only_state_at_or_before_query_time` | Pass |
| U-2 | [test_recommendation_models.py](tests/test_recommendation_models.py) | `AvailabilityTests.test_filter_excludes_known_unavailable_and_keeps_unknown` | Pass |
| U-3 | [test_recommendation_models.py](tests/test_recommendation_models.py) | `AvailabilityTests.test_metrics_use_original_rank_and_known_relevance` | Pass |
| F-1 | [test_pipeline.py](tests/test_pipeline.py) | `PipelineTests.test_f01_offline_acquisition_audit_and_temporal_preparation` | Pass |
| F-2 | [test_pipeline.py](tests/test_pipeline.py) | `PipelineTests.test_f02_two_model_evaluation_with_small_catalog` | Pass |
| F-3 | [test_pipeline.py](tests/test_pipeline.py) | `PipelineTests.test_f03_invalid_inputs_fail_without_success_metrics` | Pass |

## Data

The four Kaggle CSV files belong in `data/raw/retailrocket/`:

- `events.csv`
- `item_properties_part1.csv`
- `item_properties_part2.csv`
- `category_tree.csv`

Raw and processed data are ignored by Git. To download the public dataset with KaggleHub:

```bash
.venv/bin/python download_dataset.py
```

The downloader copies all four CSV files from the KaggleHub cache into that directory. To reuse an existing local dataset without network access:

```bash
.venv/bin/python download_dataset.py --source-dir /path/to/retailrocket/csvs
```

`--output-dir` changes the destination; existing CSV files there are replaced by the source copies. The `available` property is 0 for unavailable and 1 for available. Missing states remain unknown.

## Reproduce

Run these commands from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python download_dataset.py
.venv/bin/python audit_data.py data/raw/retailrocket
.venv/bin/python prepare_data.py data/raw/retailrocket
.venv/bin/python recommendation_models.py data/processed
.venv/bin/python -m unittest discover -s tests -v
```

`prepare_data.py` splits events chronologically (default 80% train) and creates weighted implicit interactions (view=1, add-to-cart=3, transaction=5), binary future targets, and an availability snapshot using the latest property timestamp at or before the training cutoff.

`audit_data.py` now writes `outputs/data_quality/audit_report.json`, containing source SHA-256 fingerprints, validation failures/warnings with up to five examples each, raw-data distributions, and measured audit-stage times. It exits nonzero on an error. Run preparation only after the audit succeeds. To choose a report directory:

```bash
.venv/bin/python audit_data.py data/raw/retailrocket --output-dir outputs/data_quality
```

The reusable `retailrocket_tools` package supplies CSV contracts, atomic JSON output, validation, and descriptive profiling without adding dependencies. See [data-quality behavior](docs/data_quality.md) for checks, warning policies, report status, and limitations. The profile describes the raw dataset; it does not replace chronological evaluation or measure scaling across dataset sizes.

`requirements-lock.txt` records the environment used for the checked run; `requirements.txt` lists the direct dependencies. The existing local environment was tested; a fresh installation of the lock file has not yet been validated on other platforms. The tests use a small synthetic dataset and need no Kaggle account or network access.

`recommendation_models.py` compares global popularity with item-based cosine similarity. It reports Recall@10, NDCG@10, catalog coverage, unavailable-item exposure, unknown-state exposure, and runtime before and after filtering. Only items with training interactions can be recommended; previously seen items remain eligible. Known unavailable products are removed; unknown products remain eligible. Training-item popularity fills remaining Top 10 slots without duplicates, and `-1` pads any slots that cannot be filled.

Evaluation includes only visitors with both training history and future targets. Targets include every distinct post-cutoff item for those visitors, including unavailable and future-only items. Thus filtering may reduce recall, and future-only targets remain unrecoverable. Catalog coverage uses all items observed anywhere in the dataset as its denominator. This offline evaluation does not measure cold-start visitor performance.

## Outputs

- `data/processed/metadata.json`: split counts, cutoff, and availability-state coverage.
- `outputs/data_quality/audit_report.json`: current audit status, input fingerprints, validation and descriptive statistics.
- `outputs/popularity/metrics.json`: popularity results.
- `outputs/item_based_cosine/metrics.json`: item-based results.
- `outputs/evaluation_summary.json`: shared evaluation context.
- `docs/results/`: small, versionable JSON snapshots from the checked full-data run.
- `docs/project_spec.md`: requirements, schema, three diagram types, and selected test cases.
- `docs/project_update.md`: implementation progress, verification results, and team reflections.

Availability is evaluated at the fixed training cutoff. Results are offline and do not estimate physical inventory or causal sales impact.

Saved recommendation arrays have shape `(evaluated_visitors, k)` and contain original item IDs or `-1`. `user_indices.npy` holds row indices into `data/processed/user_ids.npy`, not original visitor IDs. JSON summaries record model parameters and Python/library versions. Runtime includes model fitting/recommendation and metric calculation, but excludes data preparation and result-file writes.

## Checked run (2026-11-16)

The chronological split contains 2,204,881 training events, 551,220 test events, and 24,735 evaluated visitors with both history and future targets. Historical availability can be matched at event time for 80.7% of all events; at the training cutoff it covers 77.7% of catalog items and 86.4% of test target pairs. Among test target pairs with a known state, 48.9% are marked unavailable.

There are 212,916 training-observed items out of 235,061 event items. Of visitors with training history, 79.7% interacted with only one distinct item. The original November 16 run passed 17 tests; the November 18 data-quality integration passes 31 tests, including the same three selected unit cases and three selected functional cases. The full-data audit reports 167 category-property values absent from the category tree; category features are currently outside the model.

Item-based cosine reached Recall@10 0.1501 and NDCG@10 0.1397 before filtering. After removing known-unavailable items, Recall@10 was 0.0837 and NDCG@10 was 0.0791; known-unavailable recommendation exposure fell from 47.7% to 0%. These figures show a relevance-availability trade-off for this fixed cutoff, not a real-world sales effect.
