import asyncio
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from week5 import create_tables, fetch_snapshot, persist_snapshot, anomaly_rule
from week6 import create_week6_tables, preprocess, apply_labels, parse_time


DB_PATH = "data/rootlens.db"
DEFAULT_TARGET = "Astronomy Shop Demo"
DEFAULT_JAEGER_URL = "http://jaeger:16686/jaeger/ui"
SOURCE_NAMES = ("Prometheus", "Jaeger", "OpenSearch")


def now():
    return datetime.now(timezone.utc).isoformat()


def connection():
    os.makedirs("data", exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def initialise():
    with connection() as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL,
            prometheus_url TEXT NOT NULL,
            jaeger_url TEXT NOT NULL,
            logs_url TEXT NOT NULL,
            poll_seconds INTEGER NOT NULL DEFAULT 30,
            updated_at TEXT NOT NULL
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT NOT NULL
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            severity TEXT NOT NULL,
            service TEXT NOT NULL,
            title TEXT NOT NULL,
            evidence TEXT NOT NULL,
            confidence INTEGER NOT NULL
            )"""
        )
        db.execute(
            """INSERT OR IGNORE INTO connections
            (id, name, prometheus_url, jaeger_url, logs_url, poll_seconds, updated_at)
            VALUES (1, ?, ?, ?, ?, 30, ?)""",
            (
                DEFAULT_TARGET,
                os.getenv("PROMETHEUS_URL", "http://prometheus:9090"),
                os.getenv("JAEGER_URL", DEFAULT_JAEGER_URL),
                os.getenv("OPENSEARCH_URL", "http://opensearch:9200"),
                now(),
            ),
        )

        create_tables(db)
        create_week6_tables(db)

        # v4 used Jaeger's root route, although Astronomy Shop serves the UI below /jaeger/ui.
        legacy = db.execute("SELECT jaeger_url FROM connections WHERE id = 1").fetchone()
        if legacy and legacy["jaeger_url"].rstrip("/") == "http://jaeger:16686":
            db.execute(
                "UPDATE connections SET jaeger_url=?, updated_at=? WHERE id=1",
                (DEFAULT_JAEGER_URL, now()),
            )


def settings():
    with connection() as db:
        return dict(db.execute("SELECT * FROM connections WHERE id = 1").fetchone())


def record(source, status, detail):
    with connection() as db:
        db.execute(
            "INSERT INTO observations (created_at, source, status, detail) VALUES (?, ?, ?, ?)",
            (now(), source, status, detail),
        )


def url(base, suffix):
    return f"{base.rstrip('/')}{suffix}"


async def collect():
    cfg = settings()
    result = {"prometheus": False, "jaeger": False, "logs": False}

    async with httpx.AsyncClient(timeout=6) as client:
        try:
            response = await client.get(
                url(cfg["prometheus_url"], "/api/v1/query"),
                params={"query": "up"},
            )
            response.raise_for_status()
            targets = len(response.json().get("data", {}).get("result", []))
            record("Prometheus", "connected", f"Metrik kaynağı erişilebilir; {targets} hedef sorgulandı.")
            result["prometheus"] = True
        except (httpx.HTTPError, ValueError) as exc:
            record("Prometheus", "unavailable", f"Metrikler sorgulanamadı: {exc}")

        try:
            response = await client.get(url(cfg["jaeger_url"], "/"))
            response.raise_for_status()
            record("Jaeger", "connected", "Trace kaynağı erişilebilir.")
            result["jaeger"] = True
        except httpx.HTTPError as exc:
            record("Jaeger", "unavailable", f"Trace kaynağına ulaşılamadı: {exc}")

        try:
            response = await client.get(url(cfg["logs_url"], "/_cat/indices"), params={"format": "json"})
            response.raise_for_status()
            record("OpenSearch", "connected", f"Log kaynağı erişilebilir; {len(response.json())} indeks bulundu.")
            result["logs"] = True
        except (httpx.HTTPError, ValueError) as exc:
            record("OpenSearch", "unavailable", f"Loglar sorgulanamadı: {exc}")

    return result


async def watcher():
    while True:
        try:
            await collect()
        except Exception:
            pass
        await asyncio.sleep(max(10, settings()["poll_seconds"]))


@asynccontextmanager
async def lifespan(app):
    initialise()
    task = asyncio.create_task(watcher())
    yield
    task.cancel()


app = FastAPI(title="RootLens", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionForm(BaseModel):
    name: str
    prometheus_url: str
    jaeger_url: str
    logs_url: str
    poll_seconds: int = 30


@app.get("/health")
def health():
    return {"status": "ok", "mode": "observability-only"}


@app.get("/connection")
def get_connection():
    return settings()


@app.put("/connection")
def update_connection(form: ConnectionForm):
    with connection() as db:
        db.execute(
            """UPDATE connections
            SET name=?, prometheus_url=?, jaeger_url=?, logs_url=?, poll_seconds=?, updated_at=?
            WHERE id=1""",
            (
                form.name.strip(),
                form.prometheus_url.strip(),
                form.jaeger_url.strip(),
                form.logs_url.strip(),
                max(10, form.poll_seconds),
                now(),
            ),
        )
    return settings()


@app.post("/collect/now")
async def collect_now():
    return await collect()


@app.get("/dashboard")
def dashboard():
    cfg = settings()
    with connection() as db:
        observations = [
            dict(row)
            for row in db.execute("SELECT * FROM observations ORDER BY id DESC LIMIT 18").fetchall()
        ]
        incidents = [
            dict(row)
            for row in db.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT 20").fetchall()
        ]

    latest = {}
    for row in observations:
        latest.setdefault(row["source"], row)
    sources = [
        {
            "name": name,
            "status": latest.get(name, {}).get("status", "waiting"),
            "detail": latest.get(name, {}).get("detail", "Henüz kontrol edilmedi."),
        }
        for name in SOURCE_NAMES
    ]
    connected = sum(item["status"] == "connected" for item in sources)
    state = "healthy" if connected == len(SOURCE_NAMES) else "attention" if connected else "waiting"

    return {
        "target": cfg["name"],
        "poll_seconds": cfg["poll_seconds"],
        "state": state,
        "sources": sources,
        "incidents": incidents,
        "last_checked": observations[0]["created_at"] if observations else None,
        "mode": "observability-only",
        "ai": {
            "status": "planned",
            "label": "Sonraki aşama",
            "description": "Bu ilk sürümde yapay zekâ modeli aktif değildir. RootLens şu an gerçek telemetriyi toplar ve kaynakların erişilebilirliğini gösterir.",
            "next_steps": [
                "Kural tabanlı anomali eşikleri",
                "Normal davranışı öğrenen anomali modeli",
                "Metrik, log ve trace kanıtlarıyla otomatik kök neden açıklaması",
            ],
        },
    }


# Week 5: live, persisted baseline dataset (independent of the dashboard UI).
@app.post("/week5/collect")
async def week5_collect():
    snapshot = await fetch_snapshot(settings())
    with connection() as db:
        run_id = persist_snapshot(db, snapshot)
    return {"run_id": run_id, **snapshot}


@app.get("/week5/samples")
def week5_samples(limit: int = 100):
    limit = min(max(limit, 1), 1000)
    with connection() as db:
        rows = db.execute("SELECT * FROM telemetry_samples ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{**dict(r), "payload": __import__("json").loads(r["payload"])} for r in rows]


@app.get("/week5/quality")
def week5_quality():
    with connection() as db:
        total = db.execute("SELECT COUNT(*) FROM telemetry_samples").fetchone()[0]
        missing = db.execute("SELECT COUNT(*) FROM telemetry_samples WHERE service='' OR metric='' OR collected_at='' OR value IS NULL").fetchone()[0]
        by_source = [dict(r) for r in db.execute("SELECT source, COUNT(*) AS count FROM telemetry_samples GROUP BY source")]
        last_run = db.execute("SELECT * FROM collection_runs ORDER BY id DESC LIMIT 1").fetchone()
    return {"total_samples": total, "missing_required_fields": missing,
            "by_source": by_source, "last_run": dict(last_run) if last_run else None,
            "note": "Kaynak erişimi ile gerçek log/trace içeriği doğrulaması farklıdır."}


@app.get("/week5/baseline")
def week5_baseline(metric: str = "request_rate", threshold: float = 10.0, limit: int = 100):
    # Explicit threshold; demonstration only, not a trained anomaly model.
    limit = min(max(limit, 1), 1000)
    with connection() as db:
        rows = db.execute("SELECT * FROM telemetry_samples WHERE metric=? ORDER BY id DESC LIMIT ?", (metric, limit)).fetchall()
    return {"metric": metric, "threshold": threshold, "method": "fixed-threshold",
            "results": [{"service": r["service"], "collected_at": r["collected_at"],
                         "value": r["value"], **anomaly_rule(metric, r["value"], threshold)} for r in rows]}


# Week 6: cleaning, service/time alignment, explicit experiment labels.
from fastapi import HTTPException
from typing import Literal, Optional

class ExperimentLabel(BaseModel):
    start_at: str
    end_at: str
    service: str
    label: Literal['normal', 'anomaly']
    root_cause_service: Optional[str] = None
    scenario: str


@app.post('/week6/labels')
def week6_add_label(item: ExperimentLabel):
    start, end = parse_time(item.start_at), parse_time(item.end_at)
    if not start or not end or start >= end:
        raise HTTPException(422, 'Geçerli saat dilimli start_at ve end_at girin; start_at < end_at olmalı')
    if not item.service.strip() or not item.scenario.strip():
        raise HTTPException(422, 'service ve scenario boş olamaz')
    if item.label == 'normal' and item.root_cause_service:
        raise HTTPException(422, 'Normal senaryoda root_cause_service girilmemeli')
    with connection() as db:
        cursor = db.execute("""INSERT INTO experiment_labels
          (start_at, end_at, service, label, root_cause_service, scenario, created_at)
          VALUES (?, ?, ?, ?, ?, ?, ?)""",
          (start.isoformat(), end.isoformat(), item.service.strip(), item.label,
           (item.root_cause_service or '').strip() or None, item.scenario.strip(), now()))
        return {'id': cursor.lastrowid, 'status': 'saved', 'note': 'Etiket deney kaydıdır; model tahmini değildir.'}


@app.get('/week6/labels')
def week6_labels():
    with connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM experiment_labels ORDER BY id DESC LIMIT 500')]


@app.get('/week6/dataset')
def week6_dataset(bucket_seconds: int = 60, limit: int = 5000):
    if not 10 <= bucket_seconds <= 3600:
        raise HTTPException(422, 'bucket_seconds 10-3600 arasında olmalı')
    if not 1 <= limit <= 20000:
        raise HTTPException(422, 'limit 1-20000 arasında olmalı')
    with connection() as db:
        # Latest observations; bounded for reproducible, responsive demo.
        rows = [dict(r) for r in db.execute('SELECT * FROM telemetry_samples ORDER BY id DESC LIMIT ?', (limit,))]
        labels = [dict(r) for r in db.execute('SELECT * FROM experiment_labels')]
    windows, stats = preprocess(rows, bucket_seconds)
    apply_labels(windows, labels)
    return {'method': 'service-and-UTC-time-window-alignment', 'bucket_seconds': bucket_seconds,
            'statistics': stats, 'windows': windows,
            'note': 'Sadece kaydedilmiş gerçek örnekler. all/unknown servisleri eşleştirmeye alınmaz. '
                    'Eksik kaynaklar açıkça belirtilir; üretilmez. Etiketler yalnızca manuel deney kayıtlarından gelir.'}


@app.get('/week6/quality')
def week6_quality(bucket_seconds: int = 60):
    data = week6_dataset(bucket_seconds=bucket_seconds)
    windows = data['windows']
    return {'statistics': data['statistics'], 'total_windows': len(windows),
            'three_source_windows': sum(len(w['sources_present']) == 3 for w in windows),
            'single_source_windows': sum(len(w['sources_present']) == 1 for w in windows),
            'unlabeled_windows': sum(w['label'] == 'unlabeled' for w in windows),
            'conflicting_label_windows': sum(w['label'] == 'conflict' for w in windows),
            'warning': 'Kaynak erişimi, gerçek log/trace olaylarının toplandığını kanıtlamaz.'}
