"""Detect slow operations using a separate normal interval as reference."""

import json
import math
from collections import defaultdict
from statistics import median

from week6 import get_event_time, normalize_service


MIN_NORMAL_SPANS = 5


def root_cause_candidates(spans, anomalous_spans):
    by_id = {
        (span["trace_id"], span["span_id"]): span
        for span in spans
        if span["trace_id"] and span["span_id"]
    }
    candidates = [
        span for span in anomalous_spans
        if span["trace_id"] and span["span_id"] and span["kind"] not in ("SPAN_KIND_CLIENT", "3")
    ]
    upstream = set()
    for span in candidates:
        parent_id = span["parent_id"]
        visited = {span["span_id"]}
        while parent_id and parent_id not in visited:
            visited.add(parent_id)
            parent = by_id.get((span["trace_id"], parent_id))
            if parent is None:
                break
            if parent["service"] != span["service"]:
                upstream.add((span["trace_id"], parent_id))
            parent_id = parent["parent_id"]

    evidence = defaultdict(dict)
    for span in candidates:
        if (span["trace_id"], span["span_id"]) not in upstream:
            evidence[span["service"]][span["trace_id"]] = span["operation"]
    return sorted(
        [
            {
                "service": service,
                "trace_count": len(traces),
                "example_trace_id": next(iter(traces)),
                "example_operation": next(iter(traces.values())),
            }
            for service, traces in evidence.items()
        ],
        key=lambda item: (-item["trace_count"], item["service"]),
    )


def detect_latency_anomalies(rows, normal_interval, target_interval):
    normal = defaultdict(list)
    target = defaultdict(list)
    seen = set()
    for row in rows:
        try:
            payload = json.loads(row["payload"])
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        timestamp = get_event_time({"source": row["source"], "payload": payload})
        service = normalize_service(row["service"])
        operation = payload.get("name")
        value = row["value"]
        if (
            timestamp is None
            or service.lower() in ("", "unknown", "all")
            or not isinstance(operation, str)
            or not operation.strip()
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            continue

        key = (service, operation, str(payload.get("kind") or ""))
        span_id = (payload.get("trace_id"), payload.get("span_id"))
        if all(isinstance(part, str) and part for part in span_id):
            identity = span_id
        else:
            identity = (key, timestamp, value)
        if identity in seen:
            continue
        seen.add(identity)

        status = payload.get("status")
        error = isinstance(status, dict) and status.get("code") in ("STATUS_CODE_ERROR", 2, "2")
        if normal_interval[0] <= timestamp < normal_interval[1] and not error:
            normal[key].append(value)
        elif target_interval[0] <= timestamp < target_interval[1]:
            target[key].append({
                "service": service,
                "operation": operation,
                "kind": key[2],
                "trace_id": span_id[0] if isinstance(span_id[0], str) else None,
                "span_id": span_id[1] if isinstance(span_id[1], str) else None,
                "parent_id": payload.get("parent_span_id") if isinstance(payload.get("parent_span_id"), str) else None,
                "duration_ms": value,
                "error": error,
            })

    operations = []
    anomalous_spans = []
    for (service, operation, kind), spans in sorted(target.items()):
        reference = normal.get((service, operation, kind), [])
        result = {
            "service": service,
            "operation": operation,
            "span_kind": kind,
            "normal_span_count": len(reference),
            "target_span_count": len(spans),
            "target_max_ms": max(span["duration_ms"] for span in spans),
            "status": "insufficient_baseline",
        }
        slow_spans = []
        if len(reference) >= MIN_NORMAL_SPANS:
            center = median(reference)
            deviation = median(abs(value - center) for value in reference)
            # A relative and absolute floor suppress small fluctuations.
            threshold = center + max(3 * deviation, 0.5 * center, 1.0)
            slow_spans = [span for span in spans if span["duration_ms"] > threshold]
            result.update(
                normal_median_ms=center,
                threshold_ms=threshold,
                slow_span_count=len(slow_spans),
                status="normal",
            )
        error_spans = [span for span in spans if span["error"]]
        result["error_span_count"] = len(error_spans)
        if slow_spans or error_spans:
            result["status"] = "anomaly"
            anomalous_spans.extend(slow_spans)
            anomalous_spans.extend(error_spans)
        operations.append(result)

    return {
        "method": "jaeger-operation-latency-median-mad-and-error-status",
        "minimum_normal_spans_per_operation": MIN_NORMAL_SPANS,
        "normal_span_count": sum(map(len, normal.values())),
        "target_span_count": sum(map(len, target.values())),
        "anomalous_operations": sum(item["status"] == "anomaly" for item in operations),
        "operations": operations,
        "root_cause_candidates": root_cause_candidates(
            (span for spans in target.values() for span in spans), anomalous_spans
        ),
    }
