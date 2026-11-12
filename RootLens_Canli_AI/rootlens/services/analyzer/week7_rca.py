def find_root_cause(anomalies_list):
    """
    Anomali listesinden en olası kök nedeni çıkarır.
    """
    if not anomalies_list:
        return {"status": "normal", "message": "Anomali bulunamadı."}

    suspects = []
    for a in anomalies_list:
        suspects.append({
            "service": a.get("service", "unknown"),
            "confidence_score": 0.88,
            "reason": a.get("detail", "Bilinmeyen sapma")
        })

    return {
        "most_likely_root_cause": suspects[0] if suspects else None,
        "all_suspects": suspects
    }