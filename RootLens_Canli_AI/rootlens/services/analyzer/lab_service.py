"""Record real HTTP requests in the standalone Order/Payment testbed."""

import argparse
import logging
import os
import re
import runpy
import time
from pathlib import Path
from uuid import uuid4

import httpx
import uvicorn


TRACEPARENT = re.compile(r"00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}")
logger = logging.getLogger("uvicorn.error")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=("order", "payment"))
    parser.add_argument("port", type=int)
    parser.add_argument("analyzer")
    parser.add_argument("payment_url")
    args = parser.parse_args()
    os.environ["ROOTLENS_LAB"] = "1"
    os.environ["PAYMENT_URL"] = args.payment_url
    app = runpy.run_path(str(Path(__file__).resolve().parents[1] / args.service / "main.py"))["app"]
    measured_path = "/orders" if args.service == "order" else "/pay"

    @app.middleware("http")
    async def observe(request, call_next):
        if request.url.path != measured_path or request.method != "POST":
            return await call_next(request)
        match = TRACEPARENT.fullmatch(request.headers.get("traceparent", ""))
        trace_id, parent_id = match.groups() if match else (uuid4().hex, None)
        span_id = uuid4().hex[:16]
        request.state.traceparent = f"00-{trace_id}-{span_id}-01"
        started_at, started = time.time_ns(), time.perf_counter_ns()
        response = await call_next(request)
        duration_ms = (time.perf_counter_ns() - started) / 1_000_000
        try:
            async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
                result = await client.post(args.analyzer + "/lab/telemetry", json={
                    "service": args.service, "trace_id": trace_id, "span_id": span_id,
                    "parent_id": parent_id, "started_at_ns": started_at,
                    "duration_ms": duration_ms,
                    "status": response.status_code, "operation": request.url.path,
                })
                result.raise_for_status()
        except httpx.HTTPError as error:
            logger.error("RootLens telemetri kaydı başarısız: %s", error)
        return response

    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
