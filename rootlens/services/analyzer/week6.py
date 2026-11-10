
"""Week 6: auditable preprocessing of REAL stored Week-5 telemetry only.

No missing signals are synthesized.
Scenario labels must be entered explicitly.
"""

import json
import math
from collections import defaultdict
from datetime import datetime, timezone


def create_week6_tables(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS experiment_labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_at TEXT NOT NULL,
            end_at TEXT NOT NULL,
            service TEXT NOT NULL,
            label TEXT NOT NULL,
            root_cause_service TEXT,
            scenario TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)


def parse_time(value):
    try:
        if not isinstance(value, str):
            return None

        d = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if d.tzinfo is None:
            return None

        return d.astimezone(timezone.utc)

    except (ValueError, AttributeError, TypeError, OverflowError):
        return None


def normalize_service(service):
    service = str(service or "").strip()

    if service.startswith("opentelemetry-demo/"):
        service = service.split("/", 1)[1]

    return service


def get_event_time(row):
    """
    Get the timestamp for a telemetry record.

    Jaeger:
        Actual span start time.

    OpenSearch:
        Actual log event timestamp.

    Prometheus:
        Collection time as a temporary fallback because
        the current stored payload has no sample timestamp.
    """

    source = row.get("source")
    payload = row.get("payload") or {}

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            return None

    if not isinstance(payload, dict):
        return None

    if source == "Jaeger":
        try:
            nanos = int(payload["start_time_unix_nano"])

            return datetime.fromtimestamp(
                nanos / 1_000_000_000,
                tz=timezone.utc
            )

        except (
            KeyError,
            ValueError,
            TypeError,
            OverflowError,
            OSError
        ):
            return None

    if source == "OpenSearch":
        document = payload.get("document") or {}

        if not isinstance(document, dict):
            return None

        return parse_time(document.get("@timestamp"))

    if source == "Prometheus":
        return parse_time(row.get("collected_at"))

    return None


def preprocess(rows, bucket_seconds=60, include_unknown=False):

    if not 10 <= bucket_seconds <= 3600:
        raise ValueError(
            "bucket_seconds 10 ile 3600 arasında olmalı"
        )

    groups = defaultdict(lambda: defaultdict(list))

    stats = {
        "input_rows": 0,
        "accepted_rows": 0,
        "rejected_rows": 0,
        "rejection_reasons": {},
        "duplicate_rows": 0
    }

    seen = set()

    for row in rows:
        stats["input_rows"] += 1

        source = row["source"]
        service = normalize_service(row["service"])
        metric = str(row["metric"] or "").strip()

        # Use event time instead of collection time.
        timestamp = get_event_time(row)

        value = row["value"]
        reason = None

        if source not in ("Prometheus", "OpenSearch", "Jaeger"):
            reason = "unknown_source"

        elif not service or not metric or timestamp is None:
            reason = "missing_or_invalid_fields"

        elif (
            not include_unknown
            and service.lower() in ("all", "unknown")
        ):
            reason = "unattributed_service"

        elif (
            value is None
            or isinstance(value, bool)
            or not isinstance(value, (float, int))
            or not math.isfinite(value)
        ):
            reason = "invalid_numeric_value"

        if reason:
            stats["rejected_rows"] += 1

            stats["rejection_reasons"][reason] = (
                stats["rejection_reasons"].get(reason, 0) + 1
            )

            continue

        # Group records into time windows.
        bucket = (
            int(timestamp.timestamp()) // bucket_seconds
        ) * bucket_seconds

        signature = (
            source,
            service,
            metric,
            bucket,
            float(value),
            row.get("payload", "")
        )

        if signature in seen:
            stats["duplicate_rows"] += 1
            continue

        seen.add(signature)

        groups[(service, bucket)][(source, metric)].append(
            float(value)
        )

        stats["accepted_rows"] += 1

    output = []

    for (service, bucket), measures in sorted(
        groups.items(),
        key=lambda x: (x[0][1], x[0][0])
    ):

        sources = sorted({
            source for source, _ in measures
        })

        features = {
            f"{source.lower()}__{metric}": {
                "mean": sum(vals) / len(vals),
                "max": max(vals),
                "count": len(vals)
            }
            for (source, metric), vals in sorted(measures.items())
        }

        output.append({
            "service": service,

            "window_start": datetime.fromtimestamp(
                bucket,
                timezone.utc
            ).isoformat(),

            "window_end": datetime.fromtimestamp(
                bucket + bucket_seconds,
                timezone.utc
            ).isoformat(),

            "sources_present": sources,

            "sources_missing": sorted(
                set(("Prometheus", "OpenSearch", "Jaeger"))
                - set(sources)
            ),

            "source_coverage": len(sources) / 3,

            "features": features,

            "label": "unlabeled",

            "root_cause_service": None,

            "scenario": None
        })

    stats["output_windows"] = len(output)

    return output, stats


def apply_labels(windows, labels):

    for window in windows:
        start = parse_time(window["window_start"])

        matches = [
            label
            for label in labels
            if label["service"] == window["service"]
            and parse_time(label["start_at"]) is not None
            and parse_time(label["end_at"]) is not None
            and parse_time(label["start_at"])
            <= start
            < parse_time(label["end_at"])
        ]

        if len(matches) == 1:
            match = matches[0]

            window.update(
                label=match["label"],
                root_cause_service=match["root_cause_service"],
                scenario=match["scenario"]
            )

        elif len(matches) > 1:
            window["label"] = "conflict"

    return windows
