"""Retailrocket checks with failure counts and at most five examples per check."""

import csv

import numpy as np

from .contracts import AVAILABILITY_FILES, EVENT_WEIGHTS, INTEGER_MAX, NULLABLE, SCHEMAS
from .io import read_rows
from .profiling import DataProfile


class ValidationError(ValueError):
    pass


def parse_integer(value, name):
    if not value or not value.isascii() or not value.isdecimal():
        raise ValueError(f"{name}: expected a nonnegative integer, got {value!r}")
    number = int(value)
    if number > INTEGER_MAX[name]:
        raise ValueError(f"{name}: exceeds supported integer range")
    return number


def parse_row(filename, row):
    parsed = {}
    for name in SCHEMAS[filename]:
        value = row[name]
        if name in NULLABLE and value == "":
            parsed[name] = None
        elif name in INTEGER_MAX:
            parsed[name] = parse_integer(value, name)
        elif not value.strip():
            raise ValueError(f"{name}: must not be blank")
        else:
            parsed[name] = value
    if filename == "events.csv":
        if parsed["event"] not in EVENT_WEIGHTS:
            raise ValueError(f"Unknown event type: {parsed['event']}")
        if parsed["event"] == "transaction" and parsed["transactionid"] is None:
            raise ValueError("transaction events require transactionid")
    return parsed


class Checks:
    def __init__(self):
        self.entries = {}

    def add(self, name, count=0, example=None, severity="error", unit="rows"):
        entry = self.entries.setdefault(name, {
            "check": name, "severity": severity, "failure_count": 0,
            "count_unit": unit, "examples": [],
        })
        entry["failure_count"] += count
        if example is not None and len(entry["examples"]) < 5:
            entry["examples"].append(example)

    def summary(self):
        entries = [{**entry, "passed": entry["failure_count"] == 0} for entry in self.entries.values()]
        failed = sum(not e["passed"] and e["severity"] == "error" for e in entries)
        warnings = sum(not e["passed"] and e["severity"] == "warning" for e in entries)
        return {"passed": failed == 0, "check_count": len(entries), "failed_checks": failed,
                "warning_checks": warnings, "checks": entries}


def validate(raw_dir):
    """Scan raw CSVs without modifying sources; return checks plus descriptive statistics."""
    checks, profile = Checks(), DataProfile()
    category_parents = {}
    counts = {}
    history_chunks, history_rows = [], []
    history_dtype = np.dtype([("item", "<i4"), ("timestamp", "<i8"), ("state", "i1")])
    # Validate categories first so property foreign-key warnings are checked in one pass.
    order = ("category_tree.csv", "events.csv", *AVAILABILITY_FILES)
    checks.add("category_tree.unique_ids")
    checks.add("category_tree.parent_references", severity="warning")
    checks.add("properties.category_references", severity="warning")
    checks.add("properties.available_values")
    for filename in order:
        counts[filename] = 0
        checks.add(f"{filename}.structure", unit="files")
        checks.add(f"{filename}.fields")
        try:
            for line, row in read_rows(raw_dir / filename):
                counts[filename] += 1
                try:
                    parsed = parse_row(filename, row)
                except ValueError as exc:
                    checks.add(f"{filename}.fields", 1, {"line": line, "error": str(exc)})
                    continue
                if filename == "category_tree.csv":
                    category = parsed["categoryid"]
                    if category in category_parents:
                        checks.add("category_tree.unique_ids", 1, {"line": line, "categoryid": category})
                    category_parents[category] = parsed["parentid"]
                elif filename == "events.csv":
                    profile.observe_event(parsed)
                else:
                    profile.observe_property(parsed)
                    if parsed["property"] == "available":
                        if parsed["value"] not in {"0", "1"}:
                            checks.add("properties.available_values", 1,
                                       {"file": filename, "line": line, "value": parsed["value"]})
                        else:
                            history_rows.append((parsed["itemid"], parsed["timestamp"], int(parsed["value"])))
                            if len(history_rows) == 250_000:
                                history_chunks.append(np.array(history_rows, dtype=history_dtype))
                                history_rows.clear()
                    elif parsed["property"] == "categoryid":
                        try:
                            category = parse_integer(parsed["value"], "categoryid")
                        except ValueError:
                            category = None
                        if category not in category_parents:
                            checks.add("properties.category_references", 1,
                                       {"file": filename, "line": line, "value": parsed["value"]}, severity="warning")
        except (ValueError, OSError, UnicodeError, csv.Error) as exc:
            checks.add(f"{filename}.structure", 1, {"error": str(exc)}, unit="files")
        # Header-only property partitions are allowed; event/category tables must contain data.
        if filename in {"events.csv", "category_tree.csv"}:
            checks.add(f"{filename}.nonempty", int(counts[filename] == 0), unit="files")
    for category, parent in category_parents.items():
        if parent is not None and parent not in category_parents:
            checks.add("category_tree.parent_references", 1,
                       {"categoryid": category, "parentid": parent}, severity="warning")
    if history_rows:
        history_chunks.append(np.array(history_rows, dtype=history_dtype))
    history_rows.clear()
    checks.add("availability.nonempty", int(not history_chunks), unit="datasets")
    checks.add("availability.conflicting_states", unit="item/timestamp groups")
    checks.add("availability.repeated_states", severity="warning", unit="excess rows")
    if history_chunks:
        history = np.concatenate(history_chunks)
        history_chunks.clear()
        history.sort(order=("item", "timestamp", "state"))
        same_key = (history["item"][1:] == history["item"][:-1]) & (history["timestamp"][1:] == history["timestamp"][:-1])
        different = history["state"][1:] != history["state"][:-1]
        conflicts = np.flatnonzero(same_key & different)
        checks.add("availability.conflicting_states", int(conflicts.size))
        for i in conflicts[:5]:
            checks.add("availability.conflicting_states", example={
                "itemid": int(history[i]["item"]), "timestamp": int(history[i]["timestamp"]), "states": [0, 1],
            })
        checks.add("availability.repeated_states", int(np.count_nonzero(same_key & ~different)), severity="warning")
    result = checks.summary()
    result["rows_by_file"] = counts
    return result, profile.summary()
