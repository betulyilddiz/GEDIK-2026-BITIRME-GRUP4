from week6 import preprocess, apply_labels


def sample(source, service='payment', metric='latency', value=3, time='2026-10-16T10:00:12+00:00'):
    return dict(source=source, service=service, metric=metric, value=value, collected_at=time, payload='{}')


def test_alignment_and_missing_sources():
    windows, stats = preprocess([sample('Prometheus'), sample('OpenSearch', metric='error_count', value=2)])
    assert len(windows) == 1
    assert windows[0]['sources_missing'] == ['Jaeger']
    assert windows[0]['features']['prometheus__latency']['mean'] == 3
    assert stats['accepted_rows'] == 2


def test_dedup_and_unattributed():
    x = sample('Prometheus')
    windows, stats = preprocess([x, x, sample('Jaeger', service='all')])
    assert len(windows) == 1
    assert stats['duplicate_rows'] == 1
    assert stats['rejected_rows'] == 1


def test_explicit_label_only():
    windows, _ = preprocess([sample('Prometheus')])
    assert windows[0]['label'] == 'unlabeled'
    apply_labels(windows, [dict(start_at='2026-10-16T10:00:00+00:00', end_at='2026-10-16T10:01:00+00:00',
                               service='payment', label='anomaly', root_cause_service='payment', scenario='payment-slow')])
    assert windows[0]['label'] == 'anomaly'
