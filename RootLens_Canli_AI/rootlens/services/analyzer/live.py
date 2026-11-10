"""Run RootLens with real local Order and Payment HTTP services."""

import argparse
import asyncio
import json
import logging
import math
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
import uvicorn
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import main
from novelty import MIN_MODEL_WINDOWS


ROOTLENS = Path(__file__).resolve().parents[2]
WINDOW = 10
FAULT_WINDOWS = 2
PAYMENT = "http://127.0.0.1:18001"
ORDER = "http://127.0.0.1:18000"
logger = logging.getLogger("uvicorn.error")


class Observation(BaseModel):
    service: Literal["order", "payment"]
    trace_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    span_id: str = Field(pattern=r"^[0-9a-f]{16}$")
    parent_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    started_at_ns: int = Field(gt=0, le=4_102_444_800_000_000_000)
    duration_ms: float = Field(ge=0, le=60_000)
    status: int = Field(ge=100, le=599)
    operation: Literal["/orders", "/pay"]


class Experiment(BaseModel):
    scenario: Literal["slow", "down"]


def iso_time(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


@main.app.post("/lab/telemetry", status_code=201)
def record_observation(event: Observation):
    stamp = event.started_at_ns / 1e9
    timestamp = iso_time(stamp)
    failed = event.status >= 500
    samples = [
        ("Prometheus", "request_latency_ms", event.duration_ms, "ms", {"sample_timestamp": stamp}),
        ("Prometheus", "request_error", int(failed), "ratio", {"sample_timestamp": stamp}),
        ("OpenSearch", "log_event", 1, "event", {
            "id": event.span_id, "index": "rootlens-live",
            "document": {"@timestamp": timestamp, "severityText": "ERROR" if failed else "INFO",
                         "message": f"POST {event.operation} → {event.status}", "status_code": event.status},
        }),
        ("Jaeger", "span_duration_ms", event.duration_ms, "ms", {
            "trace_id": event.trace_id, "span_id": event.span_id, "parent_span_id": event.parent_id,
            "name": event.operation, "kind": "SPAN_KIND_SERVER",
            "status": {"code": "STATUS_CODE_ERROR"} if failed else {},
            "start_time_unix_nano": str(event.started_at_ns),
        }),
    ]

    with main.connection() as db:
        db.executemany(
            """INSERT INTO telemetry_samples
               (collected_at, source, service, metric, value, unit, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(timestamp, source, event.service, metric, value, unit,
              json.dumps({**payload, "origin": "rootlens-local-lab"}))
             for source, metric, value, unit, payload in samples],
        )
    return {"recorded_samples": len(samples)}


class Lab:
    def __init__(self):
        self.task = None
        self.status = {"phase": "idle"}

    def set_phase(self, phase, **details):
        self.status = {**self.status, "phase": phase, **details}

    async def experiment(self, scenario):
        normal_start = math.ceil((time.time() + 1) / WINDOW) * WINDOW
        normal_end = normal_start + MIN_MODEL_WINDOWS * WINDOW
        fault_start = normal_end + WINDOW
        target_end = fault_start + FAULT_WINDOWS * WINDOW
        parameters = {
            "normal_start": iso_time(normal_start), "normal_end": iso_time(normal_end),
            "target_start": iso_time(normal_end), "target_end": iso_time(target_end),
            "bucket_seconds": WINDOW,
        }
        try:
            async with httpx.AsyncClient(timeout=8, trust_env=False) as client:
                try:
                    await set_mode(client, "normal")
                    self.set_phase("normal", ends_at=iso_time(normal_end))
                    normal = await traffic(client, normal_start, normal_end)
                    self.set_phase("control", ends_at=iso_time(fault_start))
                    control = await traffic(client, normal_end, fault_start)
                    await set_mode(client, scenario)
                    self.set_phase("fault", ends_at=iso_time(target_end))
                    fault = await traffic(client, fault_start, target_end)
                finally:
                    await set_mode(client, "normal")
            if any(status != 200 for status, _ in normal + control):
                raise RuntimeError("Normal siparişlerden biri başarısız oldu.")
            if scenario == "down" and any(status != 502 for status, _ in fault):
                raise RuntimeError("Ödeme hatası kontrollü biçimde üretilemedi.")
            if scenario == "slow" and any(status != 200 or elapsed < 2.5 for status, elapsed in fault):
                raise RuntimeError("Ödeme gecikmesi kontrollü biçimde üretilemedi.")

            await asyncio.sleep(max(0, target_end - time.time()))
            collected = main.run_analysis(**parameters)
            if set(collected["model"]["services"]) != {"order", "payment"} or len(collected["windows"]) != 6:
                raise RuntimeError("Canlı telemetri eksik. İki servis için üç test penceresi ve normal model gerekiyor.")
            save_labels(normal_end, fault_start, target_end, scenario)
            self.set_phase("done", parameters=parameters, normal_requests=len(normal),
                           control_requests=len(control), fault_requests=len(fault))
        except (httpx.HTTPError, RuntimeError) as error:
            self.set_phase("failed", message=str(error))
        except Exception:
            logger.exception("Canlı deney sonlandırıldı")
            self.set_phase("failed", message="Canlı deney tamamlanamadı. Terminaldeki hata kaydını kontrol edin.")


async def set_mode(client, mode):
    response = await client.post(PAYMENT + "/admin/mode", json={"mode": mode})
    response.raise_for_status()


async def place_order(client):
    started = time.perf_counter()
    response = await client.post(ORDER + "/orders")
    return response.status_code, time.perf_counter() - started


async def traffic(client, lower, upper):
    tasks = []
    try:
        for bucket in range(lower, upper, WINDOW):
            for second in (1, 2, 3, 4, 5, 6):
                await asyncio.sleep(max(0, bucket + second - time.time()))
                tasks.append(asyncio.create_task(place_order(client)))
        return await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def save_labels(control_start, fault_start, fault_end, scenario):
    with main.connection() as db:
        db.executemany(
            """INSERT INTO experiment_labels
               (start_at, end_at, service, label, root_cause_service, scenario, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (iso_time(lower), iso_time(upper), service, label, root, name, main.now())
                for lower, upper, label, root, name in (
                    (control_start, fault_start, "normal", None, "live_normal"),
                    (fault_start, fault_end, "anomaly", "payment", f"live_payment_{scenario}"),
                )
                for service in ("order", "payment")
            ],
        )


lab = Lab()


@main.app.post("/lab/experiment", status_code=202)
async def start_experiment(experiment: Experiment):
    if lab.task and not lab.task.done():
        raise HTTPException(409, "Bir canlı deney zaten çalışıyor.")
    lab.status = {"phase": "starting", "scenario": experiment.scenario}
    lab.task = asyncio.create_task(lab.experiment(experiment.scenario))
    return lab.status


@main.app.get("/lab/experiment")
async def experiment_status():
    return lab.status


@asynccontextmanager
async def lifespan(_app):
    main.initialise()
    yield
    if lab.task and not lab.task.done():
        lab.task.cancel()
        await asyncio.gather(lab.task, return_exceptions=True)


def wait_for_services(children):
    deadline = time.monotonic() + 15
    with httpx.Client(timeout=0.5, trust_env=False) as client:
        while time.monotonic() < deadline:
            if any(child.poll() is not None for child in children):
                break
            try:
                for address in (ORDER, PAYMENT):
                    client.get(address + "/health").raise_for_status()
                return
            except httpx.HTTPError:
                time.sleep(0.2)
    raise SystemExit("Order ve Payment servisleri başlatılamadı. 18000 ve 18001 portlarını kontrol edin.")


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8013)
    args = parser.parse_args()
    dist = ROOTLENS / "frontend" / "dist-lab"
    if not (dist / "index.html").is_file():
        parser.error("Önce rootlens/frontend klasöründe npm run build:live çalıştırın.")
    main.DB_PATH = os.environ.get("ROOTLENS_DB_PATH", str(ROOTLENS / "data" / "live_lab.db"))
    main.app.router.lifespan_context = lifespan
    main.app.mount("/", StaticFiles(directory=dist, html=True))
    children = []
    try:
        for role, port in (("order", 18000), ("payment", 18001)):
            children.append(subprocess.Popen([
                sys.executable, str(Path(__file__).with_name("lab_service.py")),
                role, str(port), f"http://127.0.0.1:{args.port}", PAYMENT,
            ]))
        wait_for_services(children)
        uvicorn.run(main.app, host="127.0.0.1", port=args.port)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    run()
