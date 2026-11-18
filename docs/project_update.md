# Project Update: Local Review Record

Updated: 2026-11-18. Working draft; no commit, push, or submission is implied by this document. The November 16 measurements below are retained as historical evidence.

## Rubric completion checklist

| Item | Current evidence | Remaining work |
| --- | --- | --- |
| Background, scope, boundaries | `project_spec.md` section 1 | Team review |
| Work distribution | Task ownership and completion confirmed by Ang Li; recorded in spec section 1 | No member assignments pending |
| 3 functional + 3 non-functional requirements | FR-1 to FR-3 and NFR-1 to NFR-3 with priority and verification | Team confirmation |
| Data description, schema, storage, assumptions | Spec section 3 | Review assumptions against intended final scope |
| 3 architecture diagram types | Activity, sequence, class diagrams; each has description and selection rationale | Verify rendering in final PDF |
| 3 unit + 3 functional cases | Selected U-1/U-2/U-3 and F-1/F-2/F-3, with inputs, pre/postconditions, expectations | Preserve case IDs in final PDF |
| Progress against spec | Status table below and test evidence | Recheck after further changes |
| Personal development reflection | Ang Li's supplied two-paragraph draft, with two requested wording edits, included below | Final author review |
| Final submission | Source and local evidence available | Combine spec (maximum 4 pages) and check-in into one PDF; prepare code ZIP or approved GitHub access |

## Confirmed team contributions

Ang Li reported the following completed responsibilities:

| Member | Completed tasks |
| --- | --- |
| Ang Li | Select the dataset and baseline models; describe the software architecture; prepare a test plan |
| Wuxuan Wang | Measure how each step scales (do not guess); build a working skeleton |
| Abby Li | Prepare a specification |

The repository currently records preparation and per-model runtimes for one full-data size. Those observations alone do not establish how each step scales. Wuxuan Wang's existing scaling measurements should be linked or incorporated into the report to document that completed task; no scaling trend is inferred from the single-size run.

## Implementation status

| Requirement | Status | Evidence / limitation |
| --- | --- | --- |
| FR-1 | Implemented; fixture and full-data runs pass | Exact split, weights, matrices and as-of state verified by F-1; full-data preparation completed |
| FR-2 | Implemented; fixture and full-data runs pass | F-2 and supporting tests pass; all full-data lists checked for shape, uniqueness, training membership, and zero known-unavailable exposure after filtering |
| FR-3 | Implemented; fixture and full-data runs pass | U-3 hand-calculated ranking metrics; F-2 checks saved artifacts; full-run metrics retained in `results/` |
| NFR-1 | Implemented; fixture tests pass | U-1 and F-1 exclude future availability; F-2 excludes future-only candidates |
| NFR-2 | Implemented; fixture tests pass | F-1/F-2 verify mapping and shape; F-3 verifies invalid-input failures |
| NFR-3 | Implemented for current environment; portability validation pending | Offline fixtures pass; pinned installed versions and run configuration recorded. Fresh installation on another machine has not been tested. |

## Verification evidence

The November 18 data-quality integration passes 31 automated tests, including the original selected cases. The new `retailrocket_tools` package adds shared contracts, strict CSV structure checks, input fingerprints, atomic JSON output, validation diagnostics, and descriptive data profiles. Existing commands continue to work; no additional dependency is required. See `data_quality.md` for the report contract and limitations.

The full-data audit completed 17 checks with zero error-level failures. One warning check reports the same 167 category-reference rows already observed. All four input SHA-256 hashes match the November 16 baseline. Measured audit time before final report writing was 78.412 seconds: 2.273 seconds fingerprinting and 76.136 seconds validation/profiling. These are single-run measurements, not a scaling study. The raw profile has a median of one event per visitor; this is a different quantity from distinct training interactions per visitor. The report snapshot is `results/data_quality_2026-11-18.json`.

Full-data preparation and both models were rerun after the integration. Preparation metadata and evaluation results match the November 16 baseline, excluding runtime. All recommendation arrays retain shape `(24735, 10)`, unique training-observed IDs per row, and zero known-unavailable items after filtering. Preparation took 38.112 seconds; popularity and item cosine including evaluation took 1.538 and 5.259 seconds respectively. Updated source hashes and verification results are in `results/integration_2026-11-18.json`.

Run from the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python audit_data.py data/raw/retailrocket
.venv/bin/python prepare_data.py data/raw/retailrocket
.venv/bin/python recommendation_models.py data/processed
```

The November 16 regression suite contained 17 tests: 11 unit tests and 6 functional tests. All 17 passed on that date, including all six cases selected for grading. There were no observed failing tests in that run. No external download is required for the fixture tests; online Kaggle access is outside their coverage.

The full-data audit, preparation, and both-model evaluation also completed successfully on 2026-11-16. The dataset contains 2,756,101 events, 1,407,580 visitors, and 235,061 event items. The split contains 2,204,881 training events and 551,220 test events; 212,916 items have training history, and 24,735 visitors qualify for evaluation. Of visitors with training history, 79.7% have only one distinct training item, so sparse-history behavior and popularity fallback matter.

| Model / list | Recall@10 | NDCG@10 | Catalog coverage | Unavailable exposure | Unknown exposure |
| --- | ---: | ---: | ---: | ---: | ---: |
| Popularity / raw | 0.004853 | 0.003301 | 0.0043% | 50.0000% | 0.0000% |
| Popularity / filtered | 0.006365 | 0.003967 | 0.0043% | 0.0000% | 0.0000% |
| Item cosine / raw | 0.150102 | 0.139682 | 27.7983% | 47.7493% | 7.9151% |
| Item cosine / filtered | 0.083688 | 0.079072 | 14.1623% | 0.0000% | 13.9317% |

All four saved arrays have shape `(24735, 10)`, contain unique items per row, and recommend only training-observed items. Every filtered item is available or unknown at the cutoff. The full-data quality metrics match the previous saved run exactly; these repairs address edge cases without changing those aggregate results. Measured runtime was 45.664 seconds for preparation, 1.542 seconds for popularity including evaluation, and 5.321 seconds for item cosine including evaluation. These are observations from this machine, not performance guarantees.

The audit found zero invalid availability values and 167 category-property values absent from the category tree. Category properties are not used in ranking, but this is a data limitation if category features are added later. The installed `implicit` library emits a sparse-format conversion warning during cosine fitting; fitting completes successfully. Availability coverage and the known-unavailable target rate in metadata summarize all test target pairs, whereas model relevance metrics evaluate only visitors with history and targets.

`docs/results/` contains exact metadata/metric JSON snapshots and a validation manifest with raw-file and code SHA-256 hashes. Full arrays and raw data remain ignored by Git. The fixed-cutoff results show a relevance/availability trade-off, not an estimated sales effect.

## Specification clarifications identified during implementation

These are technical observations for the progress check, not a personal reflection:

- A candidate universe must be defined separately from ID mappings. Mappings include future-only items so test targets can be represented, while candidates require training interactions.
- A Top-K contract must define behavior for small or unavailable catalogs. The implementation now guarantees unique IDs and fixed-width arrays padded with `-1`.
- A reproducible dataset workflow must materialize CSVs at the documented path. The downloader now supports both KaggleHub acquisition and offline local-cache copying.
- The availability policy must state that unknown means eligible and that unavailable future targets remain in the relevance denominator. Otherwise, the filtered recall decrease can be misinterpreted.
- Work distribution is confirmed by Ang Li, who also supplied the personal reflection below.

## Personal reflection (Ang Li)

My role in this project was to select the dataset and baseline models, document the architecture of our offline recommendation pipeline, and prepare the test plan. Retailrocket supported our research question because it recorded both user behavior and changes in product availability. We gave views, cart additions, and purchases different weights to reflect different levels of engagement. The design challenge I focused on was aligning those events with the product records. If a product became available after the training cutoff, using that update would give the filter information it would not have had at the time. In `prepare_data.py`, the pipeline therefore uses the latest availability record at or before the cutoff and marks items with no earlier record as unknown. This helped me see that choosing a dataset also means checking whether its timestamps let us reconstruct the conditions we want to evaluate.

Writing the test plan showed me the value of keeping candidate generation, filtering, and evaluation in separate functions. The popularity baseline and the item-based cosine model produce different rankings, but both use the same filter and are evaluated against the same future interactions. Saving both versions of each ranking made the trade-off measurable. For the cosine model, filtering reduced known-unavailable exposure at the cutoff from 47.7% to zero, while Recall@10 fell from 15.0% to 8.4%. The function boundaries also gave me concrete test cases, such as checking that the filter removes known-unavailable items, keeps items with unknown status, and fills remaining slots with eligible, nonduplicate items from the popularity ranking. In a future version, I would move ranking, filtering, and evaluation into separate modules and document the candidate format up front, including how rows map to users and how empty slots are represented. That would make it easier to add another model and evaluate it under the same conditions.
