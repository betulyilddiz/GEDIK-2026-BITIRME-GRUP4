"""Run the full dashboard/API against isolated, labeled example telemetry."""

import argparse
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn
from fastapi.staticfiles import StaticFiles

import main
from week5 import persist_snapshot


START = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)
SERVICES = ("cart", "checkout", "payment")


def sample_rows():
    for minute in range(8):
        current = START + timedelta(minutes=minute, seconds=8)
        timestamp = int(current.timestamp())
        for service in SERVICES:
            affected = minute in (5, 6) and service in ("checkout", "payment")
            failed = minute == 6 and affected
            duration = {"checkout": 35, "payment": 15, "cart": 10}[service]
            if affected:
                duration *= {"checkout": 8, "payment": 18}[service]
            metric_values = {
                "up": 1,
                "request_rate": 12 if minute == 7 and service == "cart" else 2,
                "error_rate": 1 if failed else 0,
            }
            for metric, value in metric_values.items():
                yield {
                    "source": "Prometheus", "service": service, "metric": metric, "value": value,
                    "unit": "boolean" if metric == "up" else "per_second",
                    "payload": {"sample_timestamp": timestamp},
                }
            for index in range(2):
                yield {
                    "source": "OpenSearch", "service": service, "metric": "log_event",
                    "value": 1, "unit": "event", "payload": {
                        "id": f"{minute}-{service}-{index}", "index": "rootlens-example",
                        "document": {"@timestamp": current.isoformat(), "severityText": "ERROR" if failed else "INFO"},
                    },
                }
            for index in range(3):
                yield {
                    "source": "Jaeger", "service": service, "metric": "span_duration_ms",
                    "value": duration + index, "unit": "ms", "payload": {
                        "trace_id": f"example-{minute}-{index}",
                        "span_id": service,
                        "parent_span_id": None if service == "checkout" else "checkout",
                        "name": {"checkout": "PlaceOrder", "payment": "Charge", "cart": "GetCart"}[service],
                        "kind": "SPAN_KIND_SERVER",
                        "status": {"code": "STATUS_CODE_ERROR"} if failed else {},
                        "start_time_unix_nano": str((timestamp + index) * 10**9),
                    },
                }


def populate():
    samples = list(sample_rows())
    with main.connection() as db:
        persist_snapshot(db, {
            "samples": samples, "sample_count": len(samples),
            "collected_at": START.isoformat(), "status": "complete",
            "sources": {source: "example" for source in main.SOURCE_NAMES}, "issues": [],
        })
        for minute in range(4, 8):
            start = START + timedelta(minutes=minute)
            end = start + timedelta(minutes=1)
            for service in SERVICES:
                affected = minute in (5, 6) and service in ("checkout", "payment")
                scenario = {5: "payment_slow", 6: "payment_failure"}.get(minute, "normal")
                db.execute(
                    """INSERT INTO experiment_labels
                       (start_at, end_at, service, label, root_cause_service, scenario, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (start.isoformat(), end.isoformat(), service, "anomaly" if affected else "normal",
                     "payment" if affected else None, scenario, START.isoformat()),
                )
        db.execute("UPDATE connections SET name = 'RootLens örnek veri provası' WHERE id = 1")
    for source in main.SOURCE_NAMES:
        main.record(source, "connected", "Yerel prova için hazırlanmış örnek telemetri.")


@asynccontextmanager
async def lifespan(_app):
    original = main.DB_PATH
    with TemporaryDirectory(prefix="rootlens-example-") as directory:
        main.DB_PATH = str(Path(directory) / "example.db")
        try:
            main.initialise()
            populate()
            yield
        finally:
            main.DB_PATH = original


@main.app.get("/analysis/preset")
def preset():
    return {
        "normal_start": START.isoformat(),
        "normal_end": (START + timedelta(minutes=4)).isoformat(),
        "target_start": (START + timedelta(minutes=4)).isoformat(),
        "target_end": (START + timedelta(minutes=8)).isoformat(),
        "bucket_seconds": 60,
    }


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8012)
    args = parser.parse_args()
    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if not (dist / "index.html").is_file():
        parser.error("Önce rootlens/frontend klasöründe npm run build:preview çalıştırın.")
    main.app.router.lifespan_context = lifespan
    main.app.mount("/", StaticFiles(directory=dist, html=True))
    uvicorn.run(main.app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    run()
