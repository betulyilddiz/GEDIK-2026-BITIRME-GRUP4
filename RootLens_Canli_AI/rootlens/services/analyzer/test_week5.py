import asyncio
import main
from week5 import anomaly_rule, persist_snapshot


def test_threshold_baseline():
    assert anomaly_rule('latency', 120, 100)['anomaly'] is True
    assert anomaly_rule('latency', 80, 100)['anomaly'] is False
    assert anomaly_rule('latency', None, 100)['status'] == 'no_data'


def test_snapshot_persistence(monkeypatch, tmp_path):
    monkeypatch.setattr(main, 'DB_PATH', str(tmp_path / 'week5.db'))
    main.initialise()
    snapshot = {'collected_at': '2026-10-15T10:00:00+00:00', 'sources': {'Prometheus': 'ok'},
                'status': 'complete', 'issues': [], 'sample_count': 1,
                'samples': [{'source': 'Prometheus', 'service': 'payment', 'metric': 'up',
                             'value': 1, 'unit': 'boolean', 'payload': {'job': 'payment'}}]}
    with main.connection() as db:
        assert persist_snapshot(db, snapshot) == 1
    assert main.week5_quality()['total_samples'] == 1
    assert main.week5_quality()['missing_required_fields'] == 0
    assert main.week5_baseline(metric='up', threshold=0.5)['results'][0]['anomaly']


def test_collects_dated_astronomy_log_indices(monkeypatch):
    import httpx
    import week5

    async def response(request):
        if request.url.host == "logs":
            assert request.url.path == "/otel-logs*,ss4o_logs-*/_search"
            assert request.url.params["ignore_unavailable"] == "true"
            return httpx.Response(200, json={"hits": {"hits": [{
                "_index": "otel-logs-2026-11-08",
                "_id": "payment-failure",
                "_source": {
                    "@timestamp": "2026-11-08T11:40:00+00:00",
                    "resource.attributes.service.name": "payment",
                    "severityText": "ERROR",
                },
            }]}})
        if request.url.host == "prometheus":
            return httpx.Response(200, json={"status": "success", "data": {"result": []}})
        return httpx.Response(200, json={"services": []})

    async_client = httpx.AsyncClient
    transport = httpx.MockTransport(response)
    monkeypatch.setattr(week5.httpx, "AsyncClient", lambda **options: async_client(transport=transport, **options))
    snapshot = asyncio.run(week5.fetch_snapshot({
        "prometheus_url": "http://prometheus",
        "logs_url": "http://logs",
        "jaeger_url": "http://jaeger/jaeger/ui",
    }, queries={"up": "up"}))
    assert snapshot["sources"]["OpenSearch"] == "ok"
    assert snapshot["samples"][0]["service"] == "payment"
