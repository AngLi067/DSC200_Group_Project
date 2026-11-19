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
| Personal development reflection | Ang Li's revised reflection and Wuxuan Wang's reflection transcribed from the supplied screenshot, included below | Final author review |
| Final submission | Source and local evidence available | Combine spec (maximum 4 pages) and check-in into one PDF; prepare code ZIP or approved GitHub access |

## Confirmed team contributions

Ang Li reported the following completed responsibilities:

| Member | Completed tasks |
| --- | --- |
| Ang Li | Select the dataset and baseline models; describe the software architecture; prepare a test plan |
| Wuxuan Wang | Measure how each step scales (do not guess); build a working skeleton |
| Abby Li | Prepare a specification |

The November 16 and 18 repository runs record preparation and per-model runtimes for one full-data size. Wuxuan Wang's reported visitor-sampling benchmarks, run on a separate copy of the project, are included below with his reflection. These are separate measurements from the repository runs documented here.

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

I selected the dataset and baseline models for our offline recommendation pipeline, documented the architecture, and prepared the test plan. Retailrocket fit our research question because it includes both user behavior and changes in product availability. We assigned different weights to views, cart additions, and purchases to represent different levels of engagement. When documenting the architecture, I focused on matching those events with the product records at the right time. Using an availability update from after the training cutoff would give the filter information it would not have had then. In `prepare_data.py`, we use the latest availability record at or before the cutoff and treat items without a record by that point as unknown. Working through this made me pay more attention to timestamps when choosing a dataset: they need to let us reconstruct what was known at the time of the evaluation.

Having separate functions for candidate generation, filtering, and evaluation made the test plan easier to write. The popularity baseline and item-based cosine model produce different rankings, but use the same filter and the same future interactions for evaluation. We saved the original and filtered rankings so we could compare them. For the cosine model, filtering reduced known-unavailable exposure at the cutoff from 47.7% to zero, while Recall@10 dropped from 15.0% to 8.4%. I could test the filtering rules individually, including whether unknown items remain eligible and whether popularity fills remaining slots with eligible items without introducing duplicates. For a future version, I would put ranking, filtering, and evaluation in separate modules. I would also define the candidate format before implementation, including how rows correspond to users and how empty slots are represented, so another model could use the same filtering and evaluation code.

## Personal reflection (Wuxuan Wang)

### Pipeline Integration and Performance

For our Retailrocket recommendation project, I examined how the preprocessing and recommendation scripts share data and how their runtime changes as the number of visitors grows. I used an AI coding assistant to run the checks and benchmarks on a separate copy of the project.

The recommendation script relies on each matrix column identifying the same product in the item ID list and the availability array. A mismatch could produce a plausible recommendation list while filtering out the wrong products. At each sample size, we checked the saved interaction weights and test targets against the raw histories of 30 visitors. We also checked 100 products against their latest recorded availability at or before the training cutoff. All sampled records matched. Tracing those values back to the source gave me a way to check the meaning of a column as well as its dimensions.

For the benchmark, we sampled visitors and retained each selected visitor’s full history. Increasing the sample from 10% to 100% raised the event count roughly tenfold. Median preprocessing time rose from 13.00 to 15.97 seconds. Loading the same product-property tables took about 12.6 seconds at every scale, accounting for nearly four fifths of full-scale processing. This measurement helped me see the practical value of saving the processed files. We can reuse them when we change model parameters and avoid paying that cost on every run.

**Table 1. Runtime and peak memory by visitor sample**

| Visitors sampled | Events | Prepare (s) | Popularity¹ (s) | Item cosine¹ (s) | Peak RSS² (MiB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10% | 275,019 | 13.001 | 0.059 | 0.222 | 255.2 |
| 25% | 692,145 | 13.423 | 0.147 | 0.528 | 380.6 |
| 50% | 1,383,082 | 14.301 | 0.291 | 1.013 | 513.2 |
| 100% | 2,756,101 | 15.972 | 0.565 | 1.826 | 648.3 |

Medians of three runs per sample. Four model threads, 50 neighbors, 100 candidates, top 10.

¹ Includes evaluation.  ² Peak resident memory for both models run sequentially in one process.

Item-based recommendation and evaluation took 0.22 seconds at the smallest scale and 1.83 seconds at full scale. The sparse training matrix used 18.4 MiB for its core arrays at full scale, while the process running both models peaked at 648.3 MiB. It also held similarity data and candidate lists. Keeping the batch size at 2,048 visitors limited the number scored in each call, but memory still rose with the sample size. To measure how much batching itself helps, I would hold the dataset fixed and vary only the batch size.

## Personal reflection (Abby Li)

My main responsibility in this project was working on the specification, but I also helped with exploratory data analysis and visualizing some of our results.

At first, I thought the specification was mostly about making sure everyone followed the same rules when writing code. But as I worked through the recommendation pipeline, I realized that these rules also affect what we're measuring. Which users we evaluate, which items count as candidates, and how incomplete Top-K lists are handled can all change the results. Even when two models use the same dataset, their results may not be comparable if they're evaluated differently. This was something I hadn't really thought about before.

One thing that surprised me was how sparse the Retailrocket dataset actually was. We had over 2.7 million interaction events, which initially sounded like a lot. But my exploratory analysis showed that 71.2% of visitors had only one recorded event. That made me wonder: how much can we really learn about someone's preferences from just one interaction? It also made me think about which users we're actually evaluating. Since our evaluation only includes users with both historical and future interactions, the results may not represent the majority of visitors. I started paying more attention to what the data could and couldn't tell us, rather than just how much data we had.

Another moment that stood out was when Recall@10 dropped from 15.01% to 8.37% after availability filtering. My first reaction was that the model had performed much worse. But then I noticed that our evaluation still counted future interactions with items marked unavailable at the training cutoff as relevant, even though those items had been removed from the recommendations. The model had fewer chances to get a hit, while the evaluation targets stayed the same. The drop was real under our evaluation setup, but it didn't necessarily mean the filtered recommendations were less useful in practice. This made me realize how easy it is to misinterpret a metric without understanding how it's calculated.

I also learned from working with AI-assisted coding tools, Jupyter, and GitHub. Even managing branches, commits, and pushing changes to a remote repository took more time than I expected. Working on the visualizations in a separate branch helped me understand why it's important to keep changes organized when several people are working on the same project.

Looking back, the biggest thing I've learned is to be more careful about trusting results just because the code runs and the numbers look reasonable. I want to get better at understanding the assumptions behind a model, questioning how it's evaluated, and explaining why its results are meaningful.
