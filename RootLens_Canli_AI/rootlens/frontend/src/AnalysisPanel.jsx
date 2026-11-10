import { useState } from "react";

const methods = [
  ["OneClassSVM", "One-Class SVM"],
  ["Fused", "Birleşik"],
  ["Prometheus", "Metrik"],
  ["OpenSearch", "Log"],
  ["Jaeger", "Trace"],
];
const sources = methods.filter(([key]) => ["Prometheus", "OpenSearch", "Jaeger"].includes(key));
const livePhases = {
  starting: "Servisler hazırlanıyor",
  normal: "Normal trafik toplanıyor",
  control: "Normal kontrol penceresi ölçülüyor",
  fault: "Kontrollü ödeme arızası uygulanıyor",
  done: "Canlı deney tamamlandı",
};
const fields = [
  ["normal_start", "Normal başlangıç"],
  ["normal_end", "Normal bitiş"],
  ["target_start", "Test başlangıcı"],
  ["target_end", "Test bitişi"],
];
const percent = (value) => value == null ? "—" : new Intl.NumberFormat("tr-TR", {
  style: "percent", maximumFractionDigits: 1,
}).format(value);
const decimal = (value) => new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(value);
const time = (value) => new Intl.DateTimeFormat("tr-TR", {
  hour: "2-digit", minute: "2-digit", second: "2-digit",
}).format(new Date(value));
const localInput = (value) => {
  const date = new Date(value);
  return new Date(date.valueOf() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 19);
};

async function request(api, path, options) {
  const response = await fetch(api + path, options);
  const body = await response.json();
  if (!response.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : "İstek tamamlanamadı. Alanları kontrol edin.");
  }
  return body;
}

export default function AnalysisPanel({ api, preview, lab }) {
  const [times, setTimes] = useState({});
  const [bucketSize, setBucketSize] = useState(60);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState(null);
  const [method, setMethod] = useState(lab ? "OneClassSVM" : "Fused");
  const [selected, setSelected] = useState("");
  const [scenario, setScenario] = useState("down");
  const [progress, setProgress] = useState("");

  async function analyze(parameters) {
    const output = await request(api, "/analysis/run?" + new URLSearchParams(parameters));
    const firstEvent = output.time_buckets.find((item) => item.rankings[method]?.length) || output.time_buckets[0];
    setSelected(firstEvent?.window_start || "");
    setResult(output);
  }

  async function run(task) {
    setBusy(true);
    setNotice("");
    try {
      await task();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  function submit(event) {
    event.preventDefault();
    setResult(null);
    run(() => analyze({
      ...Object.fromEntries(fields.map(([key]) => [key, new Date(times[key]).toISOString()])),
      bucket_seconds: bucketSize,
    }));
  }

  function loadExample() {
    run(async () => {
      const preset = await request(api, "/analysis/preset");
      setTimes(Object.fromEntries(fields.map(([key]) => [key, localInput(preset[key])])));
      setBucketSize(preset.bucket_seconds);
      await analyze(preset);
    });
  }

  function startLive() {
    setResult(null);
    run(async () => {
      setProgress(livePhases.starting);
      try {
        await request(api, "/lab/experiment", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scenario }),
        });
        while (true) {
          const status = await request(api, "/lab/experiment");
          if (status.phase === "failed") throw new Error(status.message);
          if (status.phase === "done") {
            await analyze(status.parameters);
            setNotice(`${status.normal_requests} normal eğitim, ${status.control_requests} kontrol ve ${status.fault_requests} arızalı HTTP isteği ölçüldü.`);
            break;
          }
          const remaining = status.ends_at ? Math.max(0, Math.ceil((new Date(status.ends_at) - Date.now()) / 1000)) : null;
          setProgress(livePhases[status.phase] + (remaining == null ? "" : ` · ${remaining} sn`));
          await new Promise((resolve) => setTimeout(resolve, 1000));
        }
      } finally {
        setProgress("");
      }
    });
  }

  function collect() {
    run(async () => {
      const snapshot = await request(api, "/week5/collect", { method: "POST" });
      const counts = snapshot.samples.reduce((counts, sample) => {
        counts[sample.source] = (counts[sample.source] || 0) + 1;
        return counts;
      }, {});
      setNotice(sources.map(([key, label]) => label + " " + (counts[key] || 0)).join(" · ")
        + (snapshot.issues.length ? " · Bazı kaynaklarda toplama eksik." : " · Örnekler kaydedildi."));
    });
  }

  const bucket = result?.time_buckets.find((item) => item.window_start === selected);
  const windows = result?.windows.filter((item) => item.window_start === selected) || [];

  function label(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    run(async () => {
      await request(api, "/week6/labels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_at: bucket.window_start, end_at: bucket.window_end,
          service: form.get("service"), label: form.get("label"),
          root_cause_service: form.get("root") || null, scenario: form.get("scenario"),
        }),
      });
      setNotice("Etiket kaydedildi. Karşılaştırmayı güncellemek için analizi tekrar çalıştırın.");
    });
  }

  return (
    <div className="analysis-stack">
      <section className="content-panel analysis-setup">
        <p className="eyebrow">01 / DENEY KURULUMU</p>
        <h2>{lab ? "Canlı ödeme deneyini çalıştır" : "Normal çalışma ve test aralığı"}</h2>
        <p className="muted-copy">
          {lab
            ? "Order ve Payment servisleri gerçek HTTP istekleriyle çalışır. Yerel uygulama metrikleri, logları ve trace kayıtları anlık ölçülür. Deney yaklaşık 90–100 saniye sürer."
            : "Aynı zaman pencerelerinde tek kaynaklı, birleşik ve One-Class SVM sonuçlarını karşılaştırın."}
          {preview && " Bu prova yapay örnek telemetri kullanıyor."}
          {!preview && !lab && " One-Class SVM için servis başına en az altı tam normal pencere seçin."}
        </p>
        {lab ? (
          <div className="analysis-controls">
            <label className="analysis-select">
              Arıza senaryosu
              <select value={scenario} onChange={(event) => setScenario(event.target.value)} disabled={busy}>
                <option value="down">Ödeme hatası (HTTP 503)</option>
                <option value="slow">Ödeme gecikmesi (3 saniye)</option>
              </select>
            </label>
            <button className="primary-button" onClick={startLive} disabled={busy}>
              {busy ? "Deney sürüyor…" : "Canlı deneyi başlat"}
            </button>
          </div>
        ) : preview ? (
          <button className="refresh-button" onClick={loadExample} disabled={busy}>Örnek ödeme deneyini aç</button>
        ) : (
          <button className="refresh-button" onClick={collect} disabled={busy}>Telemetriyi kaydet</button>
        )}
        {!lab && <form onSubmit={submit}>
          <div className="form-grid">
            {fields.map(([key, name]) => (
              <label key={key}>
                {name}
                <input type="datetime-local" step="1" required value={times[key] || ""}
                  onChange={(event) => setTimes({ ...times, [key]: event.target.value })} />
              </label>
            ))}
            <label>
              Pencere uzunluğu (saniye)
              <input type="number" min="10" max="3600" required value={bucketSize}
                onChange={(event) => setBucketSize(event.target.value)} />
            </label>
          </div>
          <button className="primary-button" disabled={busy}>
            {busy ? "İşleniyor…" : "Analizi çalıştır"}
          </button>
        </form>}
        {progress && <p className="analysis-status" role="status">{progress}</p>}
        {notice && <p className="analysis-status" role="status">{notice}</p>}
      </section>

      {result && (
        <>
          <div className="analysis-kpis" aria-live="polite">
            <Kpi label="Normal referans" value={result.reference_windows} detail="Servis penceresi" />
            <Kpi label="Test aralığı" value={result.windows.length} detail="Gözlenen servis penceresi" />
            <Kpi label="Ortak değerlendirme" value={result.evaluation.common_windows} detail="Tablodaki tüm yöntemlerde ölçülebilen etiketli pencereler" />
          </div>
          <section className="content-panel">
            <p className="eyebrow">MAKİNE ÖĞRENMESİ</p>
            <h2>One-Class SVM · RBF</h2>
            <p className="muted-copy">Model, önceki normal pencerelerdeki servis davranışını öğrenir. Anomali etiketleri yalnızca sonuçları değerlendirmek için kullanılır.</p>
            {Object.keys(result.model.services).length ? (
              <ul className="analysis-model">
                {Object.entries(result.model.services).map(([service, model]) => (
                  <li key={service}>
                    <strong>{service}</strong> · {model.training_windows} normal pencere · {model.features.length} özellik
                  </li>
                ))}
              </ul>
            ) : <p className="muted-copy">Eğitim için servis başına en az {result.model.minimum_reference_windows} normal pencere ve en az iki telemetri türü gerekir.</p>}
          </section>
          {bucket ? (
            <section className="content-panel">
              <p className="eyebrow">02 / ANOMALİ VE KÖK NEDEN</p>
              <h2>Servislerin anomali skorları</h2>
              <div className="analysis-controls">
                <div className="analysis-tabs" aria-label="Analiz yöntemi">
                  {methods.map(([key, name]) => (
                    <button key={key} type="button" aria-pressed={method === key} onClick={() => setMethod(key)}>{name}</button>
                  ))}
                </div>
                <label className="analysis-select">
                  Zaman penceresi
                  <select value={selected} onChange={(event) => setSelected(event.target.value)}>
                    {result.time_buckets.map((item) => (
                      <option key={item.window_start} value={item.window_start}>
                        {time(item.window_start)} – {time(item.window_end)}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="analysis-detail">
                <div>
                  <p className="muted-copy">1 üzeri anomali. Skor üretilemeyen servislerde eksik veri veya referans var.</p>
                  {method === "OneClassSVM" && <p className="muted-copy">Alt satırlar ölçülen sinyalleri ve istatistiksel eşiklerini gösterir. Model skoru ayrı hesaplanır.</p>}
                  {windows.map((window) => (
                    <Score key={window.service} window={window} method={method} lab={lab} />
                  ))}
                </div>
                <div className="analysis-ranking">
                  <h3>Kök neden adayları</h3>
                  {bucket.rankings[method].length ? (
                    <ol>{bucket.rankings[method].map((item) => (
                      <li key={item.service}><strong>{item.service}</strong><span>{decimal(item.rank_score)}</span></li>
                    ))}</ol>
                  ) : <p className="muted-copy">Bu yöntem ve pencerede aday yok.</p>}
                  {bucket.expected_root && <p className="muted-copy">Deney etiketi · {bucket.expected_root}</p>}
                  <h3>Gözlenen servis çağrıları</h3>
                  {bucket.edges.length ? (
                    <ul>{bucket.edges.map((edge) => (
                      <li key={edge.caller + "/" + edge.callee}>
                        <span>{edge.caller} → {edge.callee}</span><span>{edge.traces} trace</span>
                      </li>
                    ))}</ul>
                  ) : <p className="muted-copy">Bu pencerede servisler arası trace bağı bulunamadı.</p>}
                </div>
              </div>
              {!preview && !lab && (
                <details className="analysis-labels">
                  <summary>Seçili pencereye deney etiketi ekle</summary>
                  <form onSubmit={label} key={selected} className="form-grid">
                    <label>Servis<select name="service" required>{windows.map(({service}) => <option key={service}>{service}</option>)}</select></label>
                    <label>Beklenen durum<select name="label"><option value="normal">Normal</option><option value="anomaly">Anomali</option></select></label>
                    <label>Senaryo adı<input name="scenario" placeholder="payment_failure" required /></label>
                    <label>Beklenen kök neden<input name="root" placeholder="Anomali varsa ör. payment" /></label>
                    <button className="primary-button" disabled={busy}>Etiketi kaydet</button>
                  </form>
                </details>
              )}
            </section>
          ) : <p className="notice">Test aralığında tam ve veri içeren pencere bulunamadı.</p>}
          <Comparison evaluation={result.evaluation} />
        </>
      )}
    </div>
  );
}

function Kpi({ label, value, detail }) {
  return <article className="analysis-kpi"><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function Score({ window, method, lab }) {
  const score = window.scores[method];
  return (
    <div className="analysis-score">
      <div><strong>{window.service}</strong><span>{score == null ? "Veri yetersiz" : decimal(score)}</span></div>
      {score != null && (
        <div className="analysis-bar" aria-hidden="true">
          <span className={score > 1 ? "alert" : ""} style={{ width: (score / 4 * 100) + "%" }} />
        </div>
      )}
      <small>{Object.entries(window.evidence)
        .filter(([source]) => ["Fused", "OneClassSVM"].includes(method) || source === method)
        .map(([source, item]) => (lab ? sources.find(([key]) => key === source)?.[1] : source)
          + " · " + item.signal + " " + decimal(item.value) + " / eşik " + decimal(item.threshold))
        .join("  |  ")}</small>
    </div>
  );
}

function Comparison({ evaluation }) {
  return (
    <section className="content-panel">
      <p className="eyebrow">03 / YÖNTEM KARŞILAŞTIRMASI</p>
      <h2>Ortak test pencerelerinde performans</h2>
      <p className="muted-copy">
        {evaluation.common_windows} / {evaluation.labeled_windows} etiketli servis penceresi ve
        {" "}{evaluation.common_root_windows} / {evaluation.labeled_root_windows} etiketli kök neden penceresi
        tabloda yer alan tüm yöntemlerde değerlendirilebildi. Çizgi, ölçüt için yeterli veri bulunmadığını gösterir.
      </p>
      <div className="analysis-table-scroll">
        <table className="analysis-table">
          <thead><tr><th>Yöntem</th><th>Kapsanan</th><th>Precision</th><th>Recall</th><th>F1</th><th>Yanlış alarm</th><th>Top-1</th><th>Top-3</th></tr></thead>
          <tbody>{methods.filter(([key]) => evaluation.methods[key]).map(([key, name]) => {
            const row = evaluation.methods[key];
            return <tr key={key}>
              <th scope="row">{name}</th><td>{row.available_labeled_windows}</td><td>{percent(row.precision)}</td>
              <td>{percent(row.recall)}</td><td>{percent(row.f1)}</td><td>{percent(row.false_alarm_rate)}</td>
              <td>{percent(row.top1)}</td><td>{percent(row.top3)}</td>
            </tr>;
          })}</tbody>
        </table>
      </div>
    </section>
  );
}
