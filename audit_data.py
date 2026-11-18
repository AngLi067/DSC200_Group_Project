"""Audit Retailrocket CSVs and write fingerprints, validation, and descriptive statistics."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import platform
from time import perf_counter
from uuid import uuid4

from retailrocket_tools.contracts import SCHEMAS
from retailrocket_tools.io import file_signature, fingerprint, write_json
from retailrocket_tools.validation import ValidationError, validate


def run_audit(data_dir: Path, output_dir: Path) -> dict:
    data_dir, output_dir = Path(data_dir).resolve(), Path(output_dir).resolve()
    if output_dir == data_dir or data_dir in output_dir.parents:
        raise ValueError("Audit output directory must be outside the raw source directory")
    report_path = output_dir / "audit_report.json"
    started = perf_counter()
    report = {
        "report_version": 1, "run_id": uuid4().hex, "status": "running",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(), "input_manifest": {}, "stage_seconds": {},
    }
    # A new run first replaces the old success status. One report is the source of truth.
    write_json(report_path, report)
    try:
        signatures = {}
        stage_started = perf_counter()
        for filename in SCHEMAS:
            path = data_dir / filename
            if not path.is_file():
                raise FileNotFoundError(f"Required file not found: {path}")
            signatures[filename] = file_signature(path)
            report["input_manifest"][filename] = fingerprint(path)
        report["stage_seconds"]["fingerprinting"] = round(perf_counter() - stage_started, 6)
        print("Source fingerprints complete; validating and profiling CSVs...", flush=True)
        stage_started = perf_counter()
        checks, profile = validate(data_dir)
        report["validation"], report["profile"] = checks, profile
        report["stage_seconds"]["validation_and_profiling"] = round(perf_counter() - stage_started, 6)
        for filename, before in signatures.items():
            if before != file_signature(data_dir / filename):
                raise ValueError(f"Source file changed during audit: {filename}")
            report["input_manifest"][filename]["parsed_records"] = checks["rows_by_file"][filename]
        if not checks["passed"]:
            failures = [entry for entry in checks["checks"] if not entry["passed"] and entry["severity"] == "error"]
            first = failures[0]
            detail = first["examples"][0] if first["examples"] else first["check"]
            raise ValidationError(f"{checks['failed_checks']} checks failed; {first['check']}: {detail}")
        report["status"] = "passed"
        report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["audit_seconds_before_final_write"] = round(perf_counter() - started, 6)
        write_json(report_path, report)
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["audit_seconds_before_final_write"] = round(perf_counter() - started, 6)
        try:
            write_json(report_path, report)
        except Exception as reporting_error:
            exc.add_note(f"Could not save failure diagnostics: {reporting_error}")
        raise
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path, nargs="?", default=Path("data/raw/retailrocket"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/data_quality"))
    args = parser.parse_args()
    try:
        report = run_audit(args.data_dir, args.output_dir)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Audit failed: {exc}\n")
    profile, checks = report["profile"], report["validation"]
    print(f"Events: {profile['events']:,}; visitors: {profile['visitors']:,}; event items: {profile['event_items']:,}")
    print(f"Event types: {profile['event_counts']}")
    print(f"Property rows: {profile['property_records']:,}; availability records: {profile['availability_records']:,}")
    print(f"Checks: {checks['check_count']}; failed: {checks['failed_checks']}; warnings: {checks['warning_checks']}")
    for check in checks["checks"]:
        if not check["passed"]:
            print(f"WARNING {check['check']}: {check['failure_count']} {check['count_unit']}")
    print(f"Audit report: {args.output_dir.resolve() / 'audit_report.json'}")


if __name__ == "__main__":
    main()
