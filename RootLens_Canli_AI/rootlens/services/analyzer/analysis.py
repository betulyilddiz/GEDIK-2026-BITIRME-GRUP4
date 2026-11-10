"""Time-separated baselines and service ranking over recorded telemetry."""

import json
from collections import Counter, defaultdict
from statistics import median

from novelty import MODEL_NAME, MIN_MODEL_WINDOWS, fit_models
from week6 import get_event_time, normalize_service, parse_time, preprocess


SOURCES = ("Prometheus", "OpenSearch", "Jaeger")
METHODS = (*SOURCES, "Fused")
RANKING_METHODS = (*METHODS, MODEL_NAME)
MIN_REFERENCE_WINDOWS = 3
MIN_FUSED_SOURCES = 2


def log_is_error(document):
    severity = document.get("severityNumber", document.get("severity_number"))
    if isinstance(severity, (int, float)) and severity > 0:
        return severity >= 17
    level = document.get("severityText") or document.get("severity_text") or document.get("severity")
    level = str(level or "").strip().upper()
    if level:
        return level in {"ERROR", "ERR", "FATAL", "CRITICAL", "SEVERE", "ALERT", "EMERGENCY"}
    return None


def telemetry_features(rows, normal, target, bucket_seconds):
    samples, spans = [], {}
    seen = set()
    for row in rows:
        source = row["source"]
        service = normalize_service(row["service"])
        if source not in SOURCES or service.lower() in ("", "unknown", "all"):
            continue
        try:
            payload = json.loads(row["payload"])
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        event = get_event_time({**row, "payload": payload})
        if event is None or not (normal[0] <= event < normal[1] or target[0] <= event < target[1]):
            continue
        bucket = int(event.timestamp()) // bucket_seconds * bucket_seconds
        if source == "Jaeger":
            trace_id, span_id = payload.get("trace_id"), payload.get("span_id")
            if isinstance(trace_id, str) and trace_id and isinstance(span_id, str) and span_id:
                identity = (source, trace_id, span_id)
                if target[0] <= event < target[1]:
                    spans.setdefault((trace_id, span_id), (service, payload.get("parent_span_id"), bucket))
            else:
                identity = (source, service, event, row["payload"])
            status = payload.get("status")
            error = isinstance(status, dict) and status.get("code") in ("STATUS_CODE_ERROR", 2, "2")
            derived = ("span_error", float(error))
        elif source == "OpenSearch":
            document = payload.get("document") or {}
            if not isinstance(document, dict):
                continue
            log_id = payload.get("id")
            identity = (source, payload.get("index"), log_id) if isinstance(log_id, str) and log_id else (
                source, service, event, row["payload"]
            )
            error = log_is_error(document)
            derived = ("log_error", float(error)) if error is not None else None
        else:
            identity = (source, service, row["metric"], event)
            derived = None

        if identity in seen:
            continue
        seen.add(identity)
        samples.append(row)
        if derived is not None:
            metric, value = derived
            samples.append({**row, "metric": metric, "value": value})
    return samples, spans


def signals(window):
    features = window["features"]
    fields = {
        "prometheus__request_rate": ("Prometheus", "İstek hızı", "mean", 0.1),
        "prometheus__error_rate": ("Prometheus", "Hata hızı", "mean", 0.05),
        "prometheus__request_latency_ms": ("Prometheus", "HTTP yanıt süresi", "mean", 2.0),
        "prometheus__request_error": ("Prometheus", "HTTP hata oranı", "mean", 0.05),
        "opensearch__log_event": ("OpenSearch", "Kayıtlı log sayısı", "count", 1.0),
        "opensearch__log_error": ("OpenSearch", "Hatalı log oranı", "mean", 0.05),
        "jaeger__span_duration_ms": ("Jaeger", "Ortalama span süresi", "mean", 1.0),
        "jaeger__span_error": ("Jaeger", "Hatalı span oranı", "mean", 0.05),
    }
    result = {
        name: (source, features[key][stat], floor)
        for key, (source, name, stat, floor) in fields.items()
        if key in features
    }
    if "prometheus__up" in features:
        result["Erişilemeyen hedef oranı"] = ("Prometheus", 1 - features["prometheus__up"]["mean"], 0.1)
    return result


def fit_reference(windows):
    reference = defaultdict(list)
    for window in windows:
        for name, (_, value, floor) in signals(window).items():
            reference[window["service"], name, floor].append(value)

    limits = {}
    for (service, name, floor), values in reference.items():
        if len(values) < MIN_REFERENCE_WINDOWS:
            continue
        center = median(values)
        mad = median(abs(value - center) for value in values)
        limits[service, name] = center + max(3 * mad, abs(center) * 0.5, floor)
    return limits


def score_window(window, limits):
    evidence = {}
    for name, (source, value, _) in signals(window).items():
        threshold = limits.get((window["service"], name))
        if threshold is None:
            continue
        score = min(4.0, max(0.0, value / threshold))
        if source not in evidence or score > evidence[source]["score"]:
            evidence[source] = {"signal": name, "value": value, "threshold": threshold, "score": score}

    scores = {source: evidence[source]["score"] if source in evidence else None for source in SOURCES}
    scores["Fused"] = (
        sum(item["score"] for item in evidence.values()) / len(evidence)
        if len(evidence) >= MIN_FUSED_SOURCES else None
    )
    return {**window, "scores": scores, "evidence": evidence}


def dependencies(spans):
    by_bucket = defaultdict(set)
    for (trace_id, _), (callee, parent_id, bucket) in spans.items():
        if not isinstance(parent_id, str) or not parent_id:
            continue
        parent = spans.get((trace_id, parent_id))
        if parent and parent[0] != callee:
            by_bucket[bucket].add((parent[0], callee, trace_id))
    return by_bucket


def rank_services(windows, method, edges):
    scores = {
        window["service"]: window["scores"][method]
        for window in windows
        if (window["scores"][method] or 0) > 1
    }
    downstream, upstream = defaultdict(set), defaultdict(set)
    if method in ("Jaeger", "Fused", MODEL_NAME):
        for caller, callee, trace_id in edges:
            if caller in scores and callee in scores:
                downstream[callee].add(trace_id)
                upstream[caller].add(trace_id)
    ranked = [
        {
            "service": service,
            "score": score,
            "rank_score": score + (0.75 if downstream[service] else 0) - (0.75 if upstream[service] else 0),
            "downstream_trace_count": len(downstream[service]),
        }
        for service, score in scores.items()
    ]
    return sorted(ranked, key=lambda item: (-item["rank_score"], item["service"]))


def label_window(window, labels):
    start, end = parse_time(window["window_start"]), parse_time(window["window_end"])
    matching = {
        (item["label"], item.get("root_cause_service"))
        for lower, upper, item in labels.get(window["service"], ())
        if lower < end and start < upper
    }
    if len(matching) != 1 or not any(
        lower <= start and end <= upper for lower, upper, _ in labels.get(window["service"], ())
    ):
        return None, None
    return next(iter(matching))


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def evaluate(windows, time_buckets):
    labeled = [window for window in windows if window["expected"] in ("normal", "anomaly")]
    methods = RANKING_METHODS if any(
        all(window["scores"][method] is not None for method in RANKING_METHODS) for window in labeled
    ) else METHODS
    common = [window for window in labeled if all(window["scores"][method] is not None for method in methods)]
    expected_buckets = [bucket for bucket in time_buckets if bucket["expected_root"]]
    common_buckets = [
        bucket for bucket in expected_buckets
        if all(bucket["assessed"][method] for method in methods)
    ]
    results = {}
    for method in methods:
        outcomes = Counter(
            (window["scores"][method] > 1, window["expected"] == "anomaly") for window in common
        )
        tp, fp, fn, tn = (outcomes[key] for key in ((True, True), (True, False), (False, True), (False, False)))
        rankings = [
            ([item["service"] for item in bucket["rankings"][method]], bucket["expected_root"])
            for bucket in common_buckets
        ]
        results[method] = {
            "available_labeled_windows": sum(window["scores"][method] is not None for window in labeled),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn),
            "f1": ratio(2 * tp, 2 * tp + fp + fn),
            "false_alarm_rate": ratio(fp, fp + tn),
            "top1": ratio(sum(root in ranked[:1] for ranked, root in rankings), len(rankings)),
            "top3": ratio(sum(root in ranked[:3] for ranked, root in rankings), len(rankings)),
            "mrr": ratio(sum(1 / (ranked.index(root) + 1) for ranked, root in rankings if root in ranked), len(rankings)),
        }
    return {
        "labeled_windows": len(labeled),
        "common_windows": len(common),
        "labeled_root_windows": len(expected_buckets),
        "common_root_windows": len(common_buckets),
        "methods": results,
    }


def analyze(rows, labels, normal, target, bucket_seconds):
    samples, spans = telemetry_features(rows, normal, target, bucket_seconds)
    windows, _ = preprocess(samples, bucket_seconds)
    references, observations = [], []
    for window in windows:
        start, end = parse_time(window["window_start"]), parse_time(window["window_end"])
        if normal[0] <= start and end <= normal[1]:
            references.append(window)
        elif target[0] <= start and end <= target[1]:
            observations.append(window)

    indexed_labels = defaultdict(list)
    for item in labels:
        start, end = parse_time(item["start_at"]), parse_time(item["end_at"])
        if start is not None and end is not None and start < end:
            indexed_labels[normalize_service(item["service"])].append((start, end, item))

    limits = fit_reference(references)
    models = fit_models(references, signals)
    by_bucket = defaultdict(list)
    scored = []
    for window in observations:
        result = score_window(window, limits)
        model = models.get(window["service"])
        result["scores"][MODEL_NAME] = model.score(signals(window)) if model else None
        result["expected"], result["expected_root"] = label_window(window, indexed_labels)
        by_bucket[int(parse_time(result["window_start"]).timestamp())].append(result)
        scored.append(result)

    edges_by_bucket = dependencies(spans)
    time_buckets = []
    for key, group in by_bucket.items():
        edges = edges_by_bucket[key]
        edge_counts = Counter((caller, callee) for caller, callee, _ in edges)
        roots = {
            normalize_service(window["expected_root"]) for window in group
            if window["expected"] == "anomaly" and window["expected_root"]
        }
        time_buckets.append({
            "window_start": group[0]["window_start"],
            "window_end": group[0]["window_end"],
            "rankings": {method: rank_services(group, method, edges) for method in RANKING_METHODS},
            "assessed": {method: any(window["scores"][method] is not None for window in group) for method in RANKING_METHODS},
            "expected_root": next(iter(roots)) if len(roots) == 1 else None,
            "edges": [
                {"caller": caller, "callee": callee, "traces": count}
                for (caller, callee), count in sorted(edge_counts.items())
            ],
        })
    return {
        "bucket_seconds": bucket_seconds,
        "minimum_reference_windows": MIN_REFERENCE_WINDOWS,
        "reference_windows": len(references),
        "model": {"name": MODEL_NAME, "minimum_reference_windows": MIN_MODEL_WINDOWS,
                  "services": {service: model.describe() for service, model in models.items()}},
        "windows": scored,
        "time_buckets": time_buckets,
        "evaluation": evaluate(scored, time_buckets),
    }
