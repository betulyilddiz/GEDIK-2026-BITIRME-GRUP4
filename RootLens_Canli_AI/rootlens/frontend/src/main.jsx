import { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import AnalysisPanel from "./AnalysisPanel";
import "./styles.css";

const preview = import.meta.env.MODE === "preview";
const lab = import.meta.env.MODE === "lab";
const api = preview || lab ? "" : import.meta.env.VITE_ANALYZER_URL || "http://localhost:8002";

const pageTitles = {
  overview: "Sistem görünümü",
  sources: "Telemetri kaynakları",
  incidents: "Olaylar",
  analysis: "Analiz ve deney",
  roadmap: "AI yol haritası",
  connect: "Sistem bağlantısı",
};

const stateLabels = {
  healthy: "Sistem bağlantıları hazır",
  attention: "Bağlantılar incelenmeli",
  waiting: "İlk kontrol bekleniyor",
};

const fallbackAi = {
  status: "available",
  label: "Analiz yöntemi",
  description:
    "One-Class SVM, normal servis pencerelerinden öğrenir ve yeni telemetrideki sapmaları işaretler.",
  next_steps: [
    "Kural tabanlı anomali eşikleri",
    "One-Class SVM ile anomali tespiti",
    "Trace ilişkileriyle kök neden sıralaması",
  ],
};

function App() {
  const [page, setPage] = useState(preview || lab ? "analysis" : "overview");
  const [data, setData] = useState(null);
  const [form, setForm] = useState(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    try {
      const response = await fetch(api + "/dashboard");
      if (!response.ok) throw new Error("Dashboard response failed");
      setData(await response.json());
    } catch {
      setNotice("RootLens analiz servisine bağlanılamadı. Docker terminalinin açık olduğundan emin ol.");
    }
  };

  useEffect(() => {
    if (lab) return;
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, []);

  const collect = async () => {
    setBusy(true);
    setNotice("Prometheus, Jaeger ve OpenSearch kontrol ediliyor...");
    try {
      const response = await fetch(api + "/collect/now", { method: "POST" });
      const result = await response.json();
      const connected = [
        result.prometheus && "Prometheus",
        result.jaeger && "Jaeger",
        result.logs && "OpenSearch",
      ]
        .filter(Boolean)
        .join(", ");
      setNotice(
        connected
          ? "Kontrol tamamlandı: " + connected + " erişilebilir."
          : "Kontrol tamamlandı; erişilebilir kaynak bulunamadı.",
      );
      await refresh();
    } catch {
      setNotice("Kontrol sırasında bağlantı kurulamadı.");
    }
    setBusy(false);
  };

  const openConnection = async () => {
    setPage("connect");
    try {
      const response = await fetch(api + "/connection");
      if (!response.ok) throw new Error("Connection response failed");
      setForm(await response.json());
    } catch {
      setNotice("Bağlantı ayarları yüklenemedi.");
    }
  };

  const saveConnection = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const response = await fetch(api + "/connection", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!response.ok) throw new Error("Save failed");
      setNotice("Sistem bağlantısı kaydedildi. RootLens izlemeye devam ediyor.");
      await refresh();
      setPage("overview");
    } catch {
      setNotice("Bağlantı ayarları kaydedilemedi.");
    }
    setBusy(false);
  };

  const ai = data?.ai || fallbackAi;
  const connectedCount = useMemo(
    () => data?.sources?.filter((source) => source.status === "connected").length || 0,
    [data],
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">R</span>
          <div>
            <strong>RootLens</strong>
            <small>Observability workspace</small>
          </div>
        </div>

        <div className="workspace-label">ÇALIŞMA ALANI</div>
        <nav>
          {!lab && <NavItem
            active={page === "overview"}
            icon="◈"
            label="Genel Bakış"
            onClick={() => setPage("overview")}
          />}
          {!lab && <NavItem
            active={page === "sources"}
            icon="◌"
            label="Telemetri"
            onClick={() => setPage("sources")}
          />}
          <NavItem
            active={page === "analysis"}
            icon="⌁"
            label="Analiz ve Deney"
            onClick={() => setPage("analysis")}
          />
          {!lab && <NavItem
            active={page === "incidents"}
            icon="△"
            label="Olaylar"
            onClick={() => setPage("incidents")}
          />}
          {!lab && <NavItem
            active={page === "roadmap"}
            icon="✦"
            label="AI Yol Haritası"
            onClick={() => setPage("roadmap")}
          />}
        </nav>

        <div className="sidebar-divider" />
        {!lab && <button className="sidebar-action" onClick={openConnection}>
          <span>⌘</span>
          Sistem Bağla
        </button>}

        <div className="sidebar-status">
          <div>
            <span className="pulse-dot" />
            {lab ? "Canlı Order ve Payment" : preview ? "Örnek veri provası" : "Canlı izleme"}
          </div>
          {!preview && !lab && <small>{data?.poll_seconds || 30} saniyede bir kontrol</small>}
        </div>
      </aside>

      <main className="main-area">
        <header className="page-header">
          <div>
            <p className="eyebrow">ROOTLENS / MİKROSERVİS GÖZLEMLENEBİLİRLİĞİ</p>
            <h1>{pageTitles[page]}</h1>
          </div>
          <div className="header-actions">
            <span className="planned-chip">{lab ? "CANLI LABORATUVAR" : preview ? "ÖRNEK VERİ" : "ROOTLENS · DENEY PANELİ"}</span>
            {!preview && !lab && <button className="refresh-button" onClick={collect} disabled={busy}>
              {busy ? "Kontrol ediliyor..." : "Şimdi yenile"}
            </button>}
          </div>
        </header>

        {notice && <div className="notice">{notice}</div>}

        {page === "overview" && (
          <Overview
            ai={ai}
            connectedCount={connectedCount}
            data={data}
            onConnect={openConnection}
            onAnalysis={() => setPage("analysis")}
          />
        )}
        {page === "sources" && <Sources data={data} onConnect={openConnection} />}
        {page === "analysis" && <AnalysisPanel api={api} preview={preview} lab={lab} />}
        {page === "incidents" && <Incidents data={data} />}
        {page === "roadmap" && <Roadmap ai={ai} />}
        {page === "connect" && (
          <ConnectionForm
            busy={busy}
            form={form}
            onSave={saveConnection}
            setForm={setForm}
          />
        )}
      </main>
    </div>
  );
}

function NavItem({ active, icon, label, onClick }) {
  return (
    <button className={"nav-item " + (active ? "active" : "")} onClick={onClick}>
      <span>{icon}</span>
      {label}
    </button>
  );
}

function Overview({ ai, connectedCount, data, onConnect, onAnalysis }) {
  const state = data?.state || "waiting";
  const sourceCount = data?.sources?.length || 3;

  return (
    <>
      <section className="demo-banner">
        <span>i</span>
        <div>
          <strong>Trace analizi Olaylar ekranında kullanılabilir.</strong>
          <p>Normal ve hatalı çalışma aralıklarını karşılaştırarak anomalileri ve kök neden adaylarını inceleyin.</p>
        </div>
      </section>

      <section className="overview-grid">
        <article className="hero-card">
          <div className="hero-topline">
            <span className={"live-badge " + state}>
              <i />
              {state === "healthy" ? "CANLI TELEMETRİ" : "BAĞLANTI DURUMU"}
            </span>
            <span className="target-name">{data?.target || "Astronomy Shop Demo"}</span>
          </div>
          <div className="hero-content">
            <div>
              <h2>{stateLabels[state]}</h2>
              <p>
                RootLens; mikroservis ortamından gelen metrik, log ve trace kaynaklarını
                tek ekranda kontrol eder.
              </p>
            </div>
            <div className={"system-orb " + state}>
              <span>{connectedCount}</span>
              <small>/{sourceCount}</small>
            </div>
          </div>
          <div className="hero-footnote">
            <span className="check-mark">✓</span>
            Kaynak sağlığını ve canlı telemetriyi izleme
          </div>
          {state === "waiting" && (
            <button className="primary-button" onClick={onConnect}>
              İlk sistemi bağla
            </button>
          )}
        </article>

        <AiPreview ai={ai} onAnalysis={onAnalysis} />
      </section>

      <section className="stat-grid">
        <StatCard
          label="Bağlı kaynak"
          value={connectedCount + "/" + sourceCount}
          note="Metrik • Trace • Log"
          tone={connectedCount === sourceCount ? "green" : "amber"}
        />
        <StatCard
          label="Açık olay"
          value={data?.incidents?.length || 0}
          note="Otomatik olay üretimi planlandı"
          tone="blue"
        />
        <StatCard
          label="Son kontrol"
          value={data?.last_checked ? "Az önce" : "Bekliyor"}
          note={(data?.poll_seconds || 30) + " sn aralıkla"}
          tone="violet"
        />
      </section>

      <section className="content-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">CANLI VERİ KATMANI</p>
            <h3>Kaynak durumu</h3>
          </div>
          <button className="text-button" onClick={onConnect}>
            Bağlantıları düzenle →
          </button>
        </div>
        <SourceList data={data} />
      </section>

      <section className="foundation-section">
        <div>
          <p className="eyebrow">MEVCUT KAPSAM</p>
          <h3>Bugün neyi gösterebiliyoruz?</h3>
          <p className="muted-copy">
            Sabit örnek veri değil, Docker üzerinde çalışan Astronomy Shop’un gerçek
            telemetrisi izleniyor.
          </p>
        </div>
        <div className="foundation-cards">
          <FoundationCard number="01" title="Metrik" text="Prometheus bağlantısı ve hedef sorgusu" />
          <FoundationCard number="02" title="Trace" text="Jaeger ile istek akışının erişilebilirliği" />
          <FoundationCard number="03" title="Log" text="OpenSearch indekslerinin kontrolü" />
        </div>
      </section>
    </>
  );
}

function AiPreview({ ai, onAnalysis }) {
  return (
    <article className="assistant-card">
      <div className="assistant-heading">
        <div>
          <span className="assistant-icon">✦</span>
          <div>
            <strong>One-Class SVM</strong>
            <small>Makine öğrenmesi</small>
          </div>
        </div>
        <span className="model-off">RBF</span>
      </div>
      <p>{ai.description}</p>
      <p className="assistant-caption">{ai.label}: {ai.next_steps[1]}</p>
      <button className="roadmap-link" onClick={onAnalysis}>
        Analiz panelini aç <span>→</span>
      </button>
    </article>
  );
}

function StatCard({ label, value, note, tone }) {
  return (
    <article className={"stat-card " + tone}>
      <div className="stat-label">{label}</div>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}

function FoundationCard({ number, title, text }) {
  return (
    <article className="foundation-card">
      <span>{number}</span>
      <strong>{title}</strong>
      <small>{text}</small>
    </article>
  );
}

function SourceList({ data }) {
  const sources = data?.sources || [
    { name: "Prometheus", status: "waiting", detail: "İlk kontrol bekleniyor." },
    { name: "Jaeger", status: "waiting", detail: "İlk kontrol bekleniyor." },
    { name: "OpenSearch", status: "waiting", detail: "İlk kontrol bekleniyor." },
  ];

  return (
    <div className="source-grid">
      {sources.map((source) => (
        <article className="source-card" key={source.name}>
          <div className="source-card-top">
            <span className={"source-dot " + source.status} />
            <strong>{source.name}</strong>
            <span className={"source-status " + source.status}>
              {source.status === "connected"
                ? "Bağlı"
                : source.status === "unavailable"
                  ? "Ulaşılamıyor"
                  : "Bekliyor"}
            </span>
          </div>
          <p>{source.detail}</p>
        </article>
      ))}
    </div>
  );
}

function Sources({ data, onConnect }) {
  return (
    <>
      <section className="content-panel source-intro">
        <p className="eyebrow">ÜÇ FARKLI KANIT</p>
        <h2>Telemetriyi tek ekranda izle</h2>
        <p>
          Bu ekran, veri kaynaklarının canlı olup olmadığını
          kontrol eder. Sonraki adımlardaki analiz bu veri katmanının üzerine kurulur.
        </p>
        <SourceList data={data} />
        <button className="primary-button" onClick={onConnect}>
          Sistem bağlantılarını aç
        </button>
      </section>

      <section className="explain-grid">
        <ExplainCard
          title="Prometheus"
          badge="METRİK"
          text="İstek sayısı, gecikme ve hata oranı gibi sayısal veriler buradan gelir."
        />
        <ExplainCard
          title="Jaeger"
          badge="TRACE"
          text="Bir isteğin hangi servislerden geçtiğini takip etmek için kullanılır."
        />
        <ExplainCard
          title="OpenSearch"
          badge="LOG"
          text="Servislerin hata ve çalışma kayıtları bu kaynakta tutulur."
        />
      </section>
    </>
  );
}

function ExplainCard({ badge, text, title }) {
  return (
    <article className="explain-card">
      <span>{badge}</span>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}

const analysisFields = [
  ["normal_start", "Normal başlangıç"],
  ["normal_end", "Normal bitiş"],
  ["target_start", "İncelenecek başlangıç"],
  ["target_end", "İncelenecek bitiş"],
];

function TraceAnalysis() {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState(null);

  const collectTraces = async () => {
    setBusy(true);
    setNotice("Telemetri kaydediliyor…");
    try {
      const response = await fetch(api + "/week5/collect", { method: "POST" });
      if (!response.ok) throw new Error();
      const snapshot = await response.json();
      const spans = snapshot.samples.filter((sample) => sample.source === "Jaeger").length;
      setNotice(
        spans
          ? `${spans} Jaeger spanı kaydedildi.`
          : "Jaeger spanı kaydedilemedi. Checkout trafiğini ve Jaeger bağlantısını kontrol edin.",
      );
    } catch {
      setNotice("Telemetri toplama isteği tamamlanamadı.");
    } finally {
      setBusy(false);
    }
  };

  const analyze = async (event) => {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    const times = new URLSearchParams(analysisFields.map(([name]) =>
      [name, new Date(fields.get(name)).toISOString()]
    ));
    setBusy(true);
    setNotice("");
    setResult(null);
    try {
      const response = await fetch(api + "/week7/anomalies?" + times);
      if (response.status === 422) {
        const error = await response.json();
        setNotice(error.detail);
      } else if (response.ok) {
        setResult(await response.json());
      } else {
        setNotice("Analiz yanıtı alınamadı.");
      }
    } catch {
      setNotice("Analiz servisine ulaşılamadı.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="content-panel">
      <p className="eyebrow">JAEGER TRACE ANALİZİ</p>
      <h2>Anomali ve kök neden adayları</h2>
      <p className="muted-copy">
        Normal ve hata senaryosunda checkout trafiği üretip telemetriyi kaydedin.
        Ardından iki aralığı bilgisayarınızın yerel saatiyle girin.
      </p>
      <button className="refresh-button" onClick={collectTraces} disabled={busy}>
        Telemetriyi kaydet
      </button>
      <form onSubmit={analyze}>
        <div className="form-grid">
          {analysisFields.map(([name, label]) => (
            <label key={name}>
              {label}
              <input type="datetime-local" step="1" name={name} required />
            </label>
          ))}
        </div>
        <button className="primary-button" disabled={busy}>Aralıkları analiz et</button>
      </form>
      {notice && <p role="status">{notice}</p>}
      {result && (
        <div className="incident-list" aria-live="polite">
          <p>
            Referans: {result.normal_span_count} span · İncelenen: {result.target_span_count} span ·
            Anomalili işlem: {result.anomalous_operations}
          </p>
          {!result.target_span_count && <p>Bu aralıkta kayıtlı Jaeger spanı bulunamadı.</p>}
          <h3>Kök neden adayları</h3>
          {result.root_cause_candidates.length ? (
            <ol>
              {result.root_cause_candidates.map((candidate) => (
                <li key={candidate.service}>
                  <strong>{candidate.service}</strong> · {candidate.trace_count} trace ·
                  Örnek işlem: {candidate.example_operation} · Trace ID: {candidate.example_trace_id}
                </li>
              ))}
            </ol>
          ) : <p>Trace kanıtıyla desteklenen aday bulunamadı.</p>}
          {result.operations.filter((item) => item.status === "anomaly").map((item) => (
            <article className="incident-row" key={JSON.stringify([item.service, item.operation, item.span_kind])}>
              <span>Anomali</span>
              <div>
                <strong>{item.service} · {item.operation}</strong>
                <p>Hatalı span: {item.error_span_count} · En uzun: {item.target_max_ms.toFixed(2)} ms</p>
                {item.threshold_ms !== undefined &&
                  <p>Gecikme eşiği: {item.threshold_ms.toFixed(2)} ms · Yavaş span: {item.slow_span_count}</p>}
              </div>
            </article>
          ))}
          {result.operations.some((item) => item.threshold_ms === undefined) &&
            <p>Bazı işlemler için en az {result.minimum_normal_spans_per_operation} normal span gerekli.</p>}
        </div>
      )}
    </section>
  );
}

function Incidents({ data }) {
  const incidents = data?.incidents || [];
  return (
    <>
      <TraceAnalysis />
      <section className="content-panel">
        <p className="eyebrow">OLAY GEÇMİŞİ</p>
        <h2>Olaylar</h2>
        <p className="muted-copy">Saklanan sistem olayları burada görünür.</p>
        {incidents.length ? (
          <div className="incident-list">
            {incidents.map((incident) => (
              <article className="incident-row" key={incident.id}>
                <span>{incident.severity}</span>
                <div>
                  <strong>{incident.title}</strong>
                  <p>{incident.evidence}</p>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <span>△</span>
            <strong>Henüz olay kaydı yok</strong>
          </div>
        )}
      </section>
    </>
  );
}

function Roadmap({ ai }) {
  const steps = [
    {
      number: "01",
      title: "Gerçek telemetriyi bağlama",
      status: "Tamamlandı",
      state: "done",
      detail: "Astronomy Shop, Docker, Prometheus, Jaeger ve OpenSearch bağlantıları.",
    },
    {
      number: "02",
      title: "Eşik ve kontrollü hata senaryoları",
      status: "Uygulandı",
      state: "done",
      detail: "Hata oranı ve gecikme için basit, açıklanabilir kurallar tanımlama.",
    },
    {
      number: "03",
      title: "Anomali tespit modeli",
      status: "Uygulandı",
      state: "done",
      detail: "Normal davranışı öğrenip olağandışı değişimleri işaretleyen One-Class SVM.",
    },
    {
      number: "04",
      title: "Otomatik kök neden açıklaması",
      status: "Uygulandı",
      state: "done",
      detail: "Metrik, log ve trace kanıtlarından servis/kök neden adayı oluşturma.",
    },
  ];

  return (
    <>
      <section className="roadmap-hero">
        <div>
          <span className="roadmap-kicker">✦ TELEMETRİ ANALİZİ</span>
          <h2>Normal davranıştan anomaliye</h2>
          <p>{ai.description}</p>
        </div>
        <div className="roadmap-hero-mark">AI</div>
      </section>

      <section className="roadmap-list">
        {steps.map((step) => (
          <article className={"roadmap-step " + step.state} key={step.number}>
            <span className="roadmap-number">{step.number}</span>
            <div>
              <div className="step-title-row">
                <h3>{step.title}</h3>
                <span>{step.status}</span>
              </div>
              <p>{step.detail}</p>
            </div>
          </article>
        ))}
      </section>

    </>
  );
}

function ConnectionForm({ busy, form, onSave, setForm }) {
  if (!form) return <div className="loading-card">Bağlantı ayarları yükleniyor...</div>;

  const change = (event) => {
    const { name, value } = event.target;
    setForm({
      ...form,
      [name]: name === "poll_seconds" ? Number(value) : value,
    });
  };

  const fields = [
    ["name", "Sistem adı", "Astronomy Shop Demo"],
    ["prometheus_url", "Prometheus adresi", "http://prometheus:9090"],
    ["jaeger_url", "Jaeger adresi", "http://jaeger:16686/jaeger/ui"],
    ["logs_url", "OpenSearch adresi", "http://opensearch:9200"],
    ["poll_seconds", "Kontrol sıklığı (saniye)", "30"],
  ];

  return (
    <form className="connection-form content-panel" onSubmit={onSave}>
      <p className="eyebrow">SİSTEM BAĞLANTISI</p>
      <h2>Mikroservis ortamını tanımla</h2>
      <p>
        RootLens bu adresleri kullanarak verileri okur. Çalışan sistemin verisini
        değiştirmez.
      </p>
      <div className="form-grid">
        {fields.map(([name, label, placeholder]) => (
          <label key={name}>
            {label}
            <input
              min={name === "poll_seconds" ? "10" : undefined}
              name={name}
              onChange={change}
              placeholder={placeholder}
              type={name === "poll_seconds" ? "number" : "text"}
              value={form[name]}
            />
          </label>
        ))}
      </div>
      <button className="primary-button" disabled={busy}>
        {busy ? "Kaydediliyor..." : "Bağlantıyı kaydet"}
      </button>
    </form>
  );
}

createRoot(document.getElementById("root")).render(<App />);
