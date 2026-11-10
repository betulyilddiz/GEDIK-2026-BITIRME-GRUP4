"""Week 5: reproducible telemetry snapshots and simple, explicit threshold baseline.

Collects real Prometheus metric samples, OpenSearch log documents, and Jaeger spans.
A successful HTTP response alone does not count as collected telemetry.
"""

import json
from datetime import datetime, timedelta, timezone

import httpx


# Upper bounds per collection run; adjust after verifying real data volume.
MAX_LOGS = 100
MAX_TRACES = 20
MAX_SPANS = 200
TRACE_LOOKBACK_MINUTES = 15
LOG_LOOKBACK_MINUTES = 15


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def create_tables(db):
    db.execute('''CREATE TABLE IF NOT EXISTS telemetry_samples (
      id INTEGER PRIMARY KEY AUTOINCREMENT, collected_at TEXT NOT NULL,
      source TEXT NOT NULL, service TEXT NOT NULL, metric TEXT NOT NULL,
      value REAL, unit TEXT NOT NULL, payload TEXT NOT NULL)''')

    db.execute('''CREATE TABLE IF NOT EXISTS collection_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT, collected_at TEXT NOT NULL,
      status TEXT NOT NULL, summary TEXT NOT NULL)''')


def anomaly_rule(metric, value, threshold):
    """Baseline only: explicitly configured numeric threshold, not an AI model."""
    if value is None:
        return {'status': 'no_data', 'anomaly': False, 'reason': 'Ãƒâ€“lÃƒÂ§ÃƒÂ¼m yok'}

    is_anomaly = float(value) > float(threshold)
    return {
        'status': 'anomaly' if is_anomaly else 'normal',
        'anomaly': is_anomaly,
        'reason': (
            f'{metric}: {value:.4g} > {threshold:.4g}'
            if is_anomaly else f'{metric}: eÃ…Å¸ik aÃ…Å¸Ã„Â±lmadÃ„Â±'
        )
    }


def _attribute_value(attr):
    value = attr.get('value', {})
    for key in ('stringValue', 'intValue', 'doubleValue', 'boolValue'):
        if key in value:
            return value[key]
    return value


def _attributes(items):
    return {a['key']: _attribute_value(a) for a in items if 'key' in a}


def _span_duration_ms(span):
    try:
        start = int(span['startTimeUnixNano'])
        end = int(span['endTimeUnixNano'])
        return max(0.0, (end - start) / 1_000_000)
    except (KeyError, TypeError, ValueError):
        return None


async def fetch_snapshot(cfg, queries=None):
    """Collect bounded live evidence; never invent or replace missing data."""
    queries = queries or {
        'up': 'up',
        'request_rate': 'sum by (service_name) (rate(http_server_duration_milliseconds_count[5m]))',
        'error_rate': '(sum by (job) (rate(rpc_server_call_duration_seconds_count{rpc_response_status_code!="OK"}[5m])) or (sum by (job) (rate(rpc_server_call_duration_seconds_count[5m])) * 0))',
    }

    now = datetime.now(timezone.utc)
    output = {
        'collected_at': now.isoformat(),
        'sources': {},
        'samples': [],
        'issues': [],
    }

    async with httpx.AsyncClient(timeout=20) as client:
        # 1. PROMETHEUS: actual metric values, not only connection status.
        prom_count = 0
        prom_errors = 0
        for metric, query in queries.items():
            try:
                r = await client.get(
                    cfg['prometheus_url'].rstrip('/') + '/api/v1/query',
                    params={'query': query},
                )
                r.raise_for_status()
                body = r.json()
                if body.get('status') != 'success':
                    raise ValueError('Prometheus response status not success')

                for item in body.get('data', {}).get('result', []):
                    raw = item.get('value', [None, None])[1]
                    try:
                        value = float(raw)
                    except (TypeError, ValueError, IndexError):
                        continue
                    if value != value or abs(value) == float('inf'):
                        continue
                    labels = item.get('metric', {})
                    service = (
                        labels.get('service_name')
                        or labels.get('service')
                        or labels.get('job')
                        or 'unknown'
                    )
                    output['samples'].append({
                        'source': 'Prometheus',
                        'service': service,
                        'metric': metric,
                        'value': value,
                        'unit': 'boolean' if metric == 'up' else 'per_second',
                        'payload': {'labels': labels, 'promql': query},
                    })
                    prom_count += 1
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                prom_errors += 1
                output['issues'].append(f'Prometheus {metric}: {exc}')

        output['sources']['Prometheus'] = (
            'ok' if prom_count and not prom_errors
            else 'partial' if prom_count else 'error' if prom_errors else 'empty'
        )
        if not prom_count:
            output['issues'].append('Prometheus: sorgular gerÃƒÂ§ek metrik ÃƒÂ¶rneÃ„Å¸i dÃƒÂ¶ndÃƒÂ¼rmedi')

        # 2. OPENSEARCH: fetch actual documents, not only index metadata.
        # The demo's indices are named otel-logs-YYYY-MM-DD.
        try:
            search_url = cfg['logs_url'].rstrip('/') + '/ss4o_logs-default-namespace/_search'
            # No fixed timestamp-field assumption: log schemas vary by collector.
            # Sort by _doc to avoid failing on unmapped timestamp fields.
            r = await client.post(
                search_url,
                json={'size': MAX_LOGS, 'query': {'range': {'@timestamp': {'gte': 'now-15m'}}}, 'sort': [{'@timestamp': {'order': 'desc'}}]},
            )
            r.raise_for_status()
            hits = r.json().get('hits', {}).get('hits', [])
            for hit in hits:
                doc = hit.get('_source', {})
                resource = doc.get('resource', {})
                resource_attrs = resource.get('attributes', {}) if isinstance(resource, dict) else {}
                if isinstance(resource_attrs, list):
                    resource_attrs = _attributes(resource_attrs)
                if not isinstance(resource_attrs, dict):
                    resource_attrs = {}
                service = (
                    doc.get('serviceName')
                    or doc.get('service_name')
                    or resource.get('service.name')
                    or resource_attrs.get('service.name')
                    or 'unknown'
                )
                output['samples'].append({
                    'source': 'OpenSearch',
                    'service': str(service),
                    'metric': 'log_event',
                    'value': 1.0,
                    'unit': 'event',
                    'payload': {'index': hit.get('_index'), 'id': hit.get('_id'), 'document': doc},
                })
            output['sources']['OpenSearch'] = 'ok' if hits else 'empty'
            if not hits:
                output['issues'].append('OpenSearch: gerÃƒÂ§ek log dokÃƒÂ¼manÃ„Â± bulunamadÃ„Â±')
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            output['sources']['OpenSearch'] = 'error'
            output['issues'].append(f'OpenSearch log search: {exc}')

        # 3. JAEGER: fetch real span contents, bounded to a recent window.
        jaeger_base = cfg['jaeger_url'].split('/jaeger/')[0].rstrip('/')
        try:
            r = await client.get(jaeger_base + '/jaeger/ui/api/v3/services')
            r.raise_for_status()
            services = r.json().get('services', [])
            # Query one representative business workflow; do not store a service list
            # and call it trace data. Can be extended to other services later.
            if 'checkout' not in services:
                output['sources']['Jaeger'] = 'empty'
                output['issues'].append('Jaeger: checkout servisi listede bulunamadÃ„Â±')
            else:
                params = {
                    'query.service_name': 'checkout',
                    'query.startTimeMin': (now - timedelta(minutes=TRACE_LOOKBACK_MINUTES)).isoformat(),
                    'query.startTimeMax': now.isoformat(),
                    'query.numTraces': str(MAX_TRACES),
                }
                r = await client.get(
                    jaeger_base + '/jaeger/ui/api/v3/traces', params=params,
                )
                r.raise_for_status()
                data = r.json().get('result', {})
                span_count = 0
                seen_traces = set()
                for resource_spans in data.get('resourceSpans', []):
                    service = str(_attributes(
                        resource_spans.get('resource', {}).get('attributes', [])
                    ).get('service.name', 'unknown'))
                    for scope in resource_spans.get('scopeSpans', []):
                        for span in scope.get('spans', []):
                            trace_id = span.get('traceId')
                            if trace_id not in seen_traces:
                                if len(seen_traces) >= MAX_TRACES:
                                    continue
                                seen_traces.add(trace_id)
                            if span_count >= MAX_SPANS:
                                break
                            duration = _span_duration_ms(span)
                            if duration is None:
                                continue
                            output['samples'].append({
                                'source': 'Jaeger',
                                'service': service,
                                'metric': 'span_duration_ms',
                                'value': duration,
                                'unit': 'ms',
                                'payload': {
                                    'trace_id': trace_id,
                                    'span_id': span.get('spanId'),
                                    'parent_span_id': span.get('parentSpanId'),
                                    'name': span.get('name'),
                                    'kind': span.get('kind'),
                                    'status': span.get('status'),
                                    'attributes': _attributes(span.get('attributes', [])),
                                    'start_time_unix_nano': span.get('startTimeUnixNano'),
                                    'end_time_unix_nano': span.get('endTimeUnixNano'),
                                },
                            })
                            span_count += 1
                        if span_count >= MAX_SPANS:
                            break
                    if span_count >= MAX_SPANS:
                        break
                output['sources']['Jaeger'] = 'ok' if span_count else 'empty'
                if not span_count:
                    output['issues'].append('Jaeger: zaman aralÃ„Â±Ã„Å¸Ã„Â±nda gerÃƒÂ§ek span bulunamadÃ„Â±')
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            output['sources']['Jaeger'] = 'error'
            output['issues'].append(f'Jaeger trace API: {exc}')

    output['sample_count'] = len(output['samples'])
    output['status'] = 'complete' if not output['issues'] else 'partial'
    return output


def persist_snapshot(db, snapshot):
    for s in snapshot['samples']:
        db.execute(
            '''INSERT INTO telemetry_samples
              (collected_at, source, service, metric, value, unit, payload)
              VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (
                snapshot['collected_at'], s['source'], s['service'], s['metric'],
                s['value'], s['unit'], json.dumps(s['payload'], ensure_ascii=False),
            ),
        )

    cur = db.execute(
        'INSERT INTO collection_runs (collected_at, status, summary) VALUES (?, ?, ?)',
        (
            snapshot['collected_at'], snapshot['status'],
            json.dumps({
                'sources': snapshot['sources'],
                'sample_count': snapshot['sample_count'],
                'issues': snapshot['issues'],
            }, ensure_ascii=False),
        ),
    )
    return cur.lastrowid
