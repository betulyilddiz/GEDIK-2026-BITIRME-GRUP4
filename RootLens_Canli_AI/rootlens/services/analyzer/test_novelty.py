from novelty import fit_models


def test_model_uses_normal_data_and_detects_an_unseen_error_rate():
    normal = [
        {
            "service": "payment",
            "signals": {
                "HTTP hata oranı": ("Prometheus", 0.0, 0.05),
                "Ortalama span süresi": ("Jaeger", 10.0 + index * 0.1, 1.0),
            },
        }
        for index in range(6)
    ]
    extract = lambda window: window["signals"]
    assert fit_models(normal[:-1], extract) == {}
    model = fit_models(normal, extract)["payment"]
    typical = normal[0]["signals"]
    unexpected = {**typical, "HTTP hata oranı": ("Prometheus", 1.0, 0.05)}
    assert model.training_windows == 6
    assert model.score(typical) <= 1
    assert model.score(unexpected) > 1
    assert model.score({"HTTP hata oranı": typical["HTTP hata oranı"]}) is None
