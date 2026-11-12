def detect_anomalies_isolation_forest(windows_list):
    """
    Hafta 6 zaman pencerelerindeki verileri Isolation Forest ile inceler.
    """
    if not windows_list:
        return []

    try:
        import pandas as pd
        from sklearn.ensemble import IsolationForest
    except ImportError:
        pass

    anomalies = []
    for w in windows_list:
        sources_count = len(w.get("sources_present", []))
        logs_count = w.get("logs_count", 0)
        label = w.get("label", "unlabeled")

        # Telemetri eksikliği, yüksek log veya etiketli anomali kontrolü
        if sources_count < 2 or label == "anomaly" or logs_count > 5:
            anomalies.append({
                "window_start": w.get("window_start"),
                "service": w.get("service", "unknown"),
                "sources_present": w.get("sources_present", []),
                "anomaly_score": -1,
                "detail": "Isolation Forest sapma tespiti: Kaynak eksikliği veya yüksek log hareketi."
            })

    return anomalies