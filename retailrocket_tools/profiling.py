"""Descriptive raw-data statistics; these are not scalability benchmarks."""

from collections import Counter

import numpy as np


class DataProfile:
    """Retain per-visitor/item summaries, not the full raw event/property tables."""

    def __init__(self):
        self.event_types = Counter()
        self.visitor_events = Counter()
        self.event_items = set()
        self.property_items = set()
        self.property_names = Counter()
        self.availability_items = set()
        self.availability_states = Counter()
        self.min_timestamp = None
        self.max_timestamp = None

    def observe_event(self, row):
        self.event_types[row["event"]] += 1
        self.visitor_events[row["visitorid"]] += 1
        self.event_items.add(row["itemid"])
        timestamp = row["timestamp"]
        self.min_timestamp = timestamp if self.min_timestamp is None else min(self.min_timestamp, timestamp)
        self.max_timestamp = timestamp if self.max_timestamp is None else max(self.max_timestamp, timestamp)

    def observe_property(self, row):
        self.property_items.add(row["itemid"])
        self.property_names[row["property"]] += 1
        if row["property"] == "available" and row["value"] in {"0", "1"}:
            self.availability_items.add(row["itemid"])
            self.availability_states[row["value"]] += 1

    def summary(self):
        counts = np.fromiter(self.visitor_events.values(), dtype=np.int64)
        distribution = None
        if counts.size:
            distribution = {
                "minimum": int(counts.min()), "maximum": int(counts.max()),
                "mean": float(counts.mean()), "median": float(np.median(counts)),
                "p90": float(np.quantile(counts, 0.9)),
                "visitors_with_one_event": int(np.count_nonzero(counts == 1)),
            }
        covered = len(self.event_items & self.availability_items)
        return {
            "scope": "all raw rows passing field/type checks; descriptive only, not model features",
            "events": sum(self.event_types.values()), "visitors": len(self.visitor_events),
            "event_items": len(self.event_items), "event_counts": dict(self.event_types),
            "event_timestamp_range_ms": [self.min_timestamp, self.max_timestamp],
            "events_per_visitor": distribution,
            "property_records": sum(self.property_names.values()), "property_items": len(self.property_items),
            "property_counts": dict(sorted(self.property_names.items())),
            "availability_records": sum(self.availability_states.values()),
            "availability_record_states": dict(self.availability_states),
            "items_with_availability_history": len(self.availability_items),
            "event_items_with_any_availability_history": covered,
            "event_items_without_any_availability_history": len(self.event_items) - covered,
            "any_time_item_availability_coverage": covered / len(self.event_items) if self.event_items else None,
            "limitations": [
                "Any-time history coverage is not availability coverage at the training cutoff.",
                "Events per visitor count repeated events, not distinct training items.",
                "No physical inventory quantities or causal sales effects are inferred.",
                "Missing item availability history is allowed; preprocessing resolves unknown states as -1.",
            ],
        }
