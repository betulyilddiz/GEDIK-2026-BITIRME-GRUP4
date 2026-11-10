from fastapi.testclient import TestClient

import main
from preview import populate, preset


def example_client(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "example.db"))
    main.initialise()
    populate()
    return TestClient(main.app)


def test_compare_methods_and_rank_payment_through_api(monkeypatch, tmp_path):
    client = example_client(monkeypatch, tmp_path)
    response = client.get("/analysis/run", params=preset())
    assert response.status_code == 200
    result = response.json()
    assert result["reference_windows"] == 12
    assert result["evaluation"]["common_windows"] == 12
    assert result["evaluation"]["common_root_windows"] == 2
    assert set(result["evaluation"]["methods"]) == {"Prometheus", "OpenSearch", "Jaeger", "Fused"}
    failure = result["time_buckets"][2]
    assert failure["rankings"]["Fused"][0]["service"] == "payment"
    assert {"caller": "checkout", "callee": "payment", "traces": 3} in failure["edges"]
    assert result["evaluation"]["methods"]["Fused"]["top1"] == 1

    with main.connection() as db:
        db.execute("DELETE FROM experiment_labels")
    unlabeled = client.get("/analysis/run", params=preset()).json()
    assert unlabeled["evaluation"]["common_windows"] == 0
    assert unlabeled["evaluation"]["methods"]["Fused"]["f1"] is None
    assert [window["scores"] for window in unlabeled["windows"]] == [
        window["scores"] for window in result["windows"]
    ]
    assert [bucket["rankings"] for bucket in unlabeled["time_buckets"]] == [
        bucket["rankings"] for bucket in result["time_buckets"]
    ]


def test_missing_sources_are_excluded_from_the_common_comparison(monkeypatch, tmp_path):
    client = example_client(monkeypatch, tmp_path)
    with main.connection() as db:
        db.execute("DELETE FROM telemetry_samples WHERE source != 'Jaeger'")
    result = client.get("/analysis/run", params=preset()).json()
    assert len(result["windows"]) == 12
    assert all(window["scores"]["Fused"] is None for window in result["windows"])
    assert result["evaluation"]["methods"]["Jaeger"]["available_labeled_windows"] == 12
    assert result["evaluation"]["methods"]["Fused"]["available_labeled_windows"] == 0
    assert result["evaluation"]["common_windows"] == 0
