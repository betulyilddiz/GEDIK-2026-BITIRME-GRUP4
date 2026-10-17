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
