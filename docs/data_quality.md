# Retailrocket data-quality integration

The supplied ingestion, validation, and profiling designs have been adapted to the current Retailrocket pipeline. This implementation uses Python CSV processing and the existing NumPy dependency. It does not require DuckDB or Instacart tables.

## Run

```bash
.venv/bin/python audit_data.py data/raw/retailrocket --output-dir outputs/data_quality
.venv/bin/python -m unittest discover -s tests -v
```

An audit returns exit status 0 only if all error-level checks pass. Inspect `outputs/data_quality/audit_report.json`; run preparation and recommendation after a successful audit. The audit is a separate command, not an implicit prerequisite automatically executed by `prepare_data.py`.

## Modules and integration

| Module | Responsibility |
| --- | --- |
| `retailrocket_tools/contracts.py` | CSV columns, integer limits, nullable fields, and event weights |
| `retailrocket_tools/io.py` | Strict CSV structure, read-only SHA-256 fingerprints, atomic JSON replacement |
| `retailrocket_tools/validation.py` | Retailrocket field checks, category warnings, conflicting availability detection, bounded error examples |
| `retailrocket_tools/profiling.py` | Event distribution, visitor activity, property counts, and availability-history coverage |
| `audit_data.py` | Command-line entry point, run status, input-change detection, combined report |

The downloader shares the expected file contract. Preprocessing shares the CSV reader and event definitions. Preprocessing and model evaluation use the atomic JSON writer. Recommendation algorithms, event weights, chronological splitting, and unknown-state filtering policy remain unchanged.

## Validation policy

**Errors stop a successful audit:** missing files; missing, unexpected or duplicate columns; malformed CSV rows; required blank fields; invalid numeric strings, negative IDs/timestamps or integer overflow; unknown event types; transaction events without a transaction ID; empty event/category tables; duplicate category IDs; availability outside 0/1; absent availability records; conflicting states for the same item and timestamp; or source files changing during the audit.

**Warnings are reported without blocking:** category-property values absent from the category tree (including malformed category values), category parents absent from the tree, and repeated identical item/timestamp/state observations. Category features are not used by the current model. Repeated user-item events are expected behavior and are not treated as duplicate primary keys.

Visitor/item IDs may be zero. Blank transaction IDs on views/carts and blank category parents are permitted. Missing item availability history is permitted and is reported as coverage information; preprocessing retains its existing unknown-state value of -1. An empty property partition is allowed if availability records exist in the other partition.

Headers may be reordered and may have a UTF-8 BOM. Empty physical lines are ignored as non-records. Malformed or invalid data records are never silently accepted: the audit fails, records diagnostic counts, and leaves source bytes unchanged. Statistics in a failed report describe only rows passing field/type checks; do not use them as a complete valid-dataset summary. A structural CSV error stops parsing that file, so its parsed-record count may be partial. Physical line counts are explicitly distinguished from CSV record counts.

## 
One `audit_report.json` is the authoritative report. It has a unique run ID and transitions from `running` to `passed` or `failed`. Starting a new audit replaces the previous status before work begins. A failed rerun therefore does not retain an earlier success marker. An interruption can leave `running`, which must not be treated as success. Use a separate output directory for each concurrently running audit.

The report contains input hashes and sizes, parsed-record counts, validation results, at most five examples per check, a raw-data profile, and measured stage times. Writes replace a complete JSON document atomically. If saving an error report itself fails, the original exception is preserved. Reports must be written outside the raw source directory.

The source signature (device, inode, byte size and modification time) is checked around hashing and again after scanning. This detects ordinary file changes during the run; inputs should remain immutable during an audit. Hashes identify the bytes actually fingerprinted.

## Interpretation and resource limits

The raw profile covers all valid input events. Events-per-visitor includes repeated events and differs from distinct training interactions per visitor. Any-time availability-history coverage can include records after the training cutoff; it is descriptive only and is not used to rank or filter recommendations. The existing preparation metadata continues to provide cutoff-aligned coverage.

Rows are scanned sequentially, but memory use is not constant: the profile retains per-visitor counters and item sets, and conflicting availability detection stores compact numeric history arrays. No global process-memory cap is claimed. Stage times describe one audit at one input size; they are not a scalability benchmark. Cross-machine installation and multiple-size performance experiments remain separate verification tasks.

## Automated checks

The integration passes 31 automated tests on 2026-11-18. The 14 new data-quality tests cover exact fixture statistics and hashes, zero IDs and structural nulls, failed reruns, bounded examples, numeric and transaction constraints, availability conflicts/repeats, duplicate categories, empty events, source/output separation, input mutation, diagnostic write failures, atomic writes, empty-file fingerprints, BOM/reordered headers, and malformed CSVs. Existing CLI functional tests now verify a successful quality report before preprocessing.
