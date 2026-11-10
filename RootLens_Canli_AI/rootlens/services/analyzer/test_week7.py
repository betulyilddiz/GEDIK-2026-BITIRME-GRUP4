import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import main


INTERVALS = {
    "normal_start": "2026-11-08T13:00:00+03:00",
    "normal_end": "2026-11-08T13:05:00+03:00",
    "target_start": "2026-11-08T13:05:00+03:00",
    "target_end": "2026-11-08T13:10:00+03:00",
}


def span(service, operation, minute, second, value, *, trace_id=None, parent_id=None, error=False):
    start = datetime(2026, 11, 8, 10, minute, second, tzinfo=timezone.utc)
    payload = json.dumps({
        "trace_id": trace_id or f"{minute}:{second}",
        "span_id": f"{service}:{operation}",
        "parent_span_id": parent_id,
        "name": operation,
        "kind": "SPAN_KIND_SERVER",
        "status": {"code": "STATUS_CODE_ERROR"} if error else {},
        "start_time_unix_nano": str(int(start.timestamp()) * 10**9),
    })
    return start.isoformat(), "Jaeger", service, "span_duration_ms", value, "ms", payload


def test_latency_comparison_through_api(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "week7.db"))
    main.initialise()
    normal = [span("payment", "Charge", 1, second, value)
              for second, value in enumerate([8, 9, 10, 11, 12])]
    normal += [span("cart", "GetCart", 1, second, 10) for second in range(5)]
    slow = span("opentelemetry-demo/payment", "Charge", 5, 0, 250)
    normal_target = span("cart", "GetCart", 5, 1, 11)
    uncalibrated = span("payment", "Validate", 5, 2, 300)
    end_boundary = span("cart", "GetCart", 10, 0, 999)
    with main.connection() as db:
        db.executemany(
            """INSERT INTO telemetry_samples
               (collected_at, source, service, metric, value, unit, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            normal + [slow, slow, normal_target, uncalibrated, end_boundary],
        )

    response = TestClient(main.app).get("/week7/anomalies", params=INTERVALS)
    assert response.status_code == 200
    result = response.json()
    assert result["anomalous_operations"] == 1
    assert result["target_span_count"] == 3
    cart, charge, validate = result["operations"]
    assert cart["status"] == "normal"
    assert charge["service"] == "payment"
    assert charge["normal_median_ms"] == 10
    assert charge["threshold_ms"] == 15
    assert charge["slow_span_count"] == 1
    assert charge["target_max_ms"] == 250
    assert validate["status"] == "insufficient_baseline"
    assert [item["service"] for item in result["root_cause_candidates"]] == ["payment"]


def test_root_cause_prefers_downstream_failure_without_a_latency_baseline(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "week7.db"))
    main.initialise()
    trace_id = "failed-checkout"
    checkout = span("checkout", "PlaceOrder", 5, 0, 300, trace_id=trace_id, error=True)
    payment = span(
        "payment", "Charge", 5, 1, 200, trace_id=trace_id,
        parent_id="checkout:PlaceOrder", error=True,
    )
    with main.connection() as db:
        db.executemany(
            """INSERT INTO telemetry_samples
               (collected_at, source, service, metric, value, unit, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [checkout, payment],
        )

    response = TestClient(main.app).get("/week7/anomalies", params=INTERVALS)
    assert response.status_code == 200
    result = response.json()
    assert result["anomalous_operations"] == 2
    assert result["root_cause_candidates"] == [{
        "service": "payment",
        "trace_count": 1,
        "example_trace_id": trace_id,
        "example_operation": "Charge",
    }]


def test_latency_comparison_rejects_overlapping_intervals():
    response = TestClient(main.app).get(
        "/week7/anomalies",
        params={**INTERVALS, "target_start": "2026-11-08T13:04:00+03:00"},
    )
    assert response.status_code == 422
