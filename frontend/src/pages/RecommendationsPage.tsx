import { useState, type FormEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiError, qs } from "../api/client";
import type { AiSummary, InsightSettings, Recommendation, RecommendationsResponse, RiskLevel } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorBox, Field, Loading, PageHeader, ProductThumb, Success } from "../components/ui";
import { money } from "../utils/format";
import { useAsync } from "../utils/useAsync";
import type { PromotionPrefill } from "./PromotionsPage";
import { Icon } from "../components/Icon";

const LEVEL: Record<RiskLevel, { badge: string; dot: string }> = {
  high: { badge: "badge-danger", dot: "dot-danger" },
  medium: { badge: "badge-warn", dot: "dot-warn" },
  low: { badge: "badge-neutral", dot: "dot-low" },
};

/** Xavf darajasi nuqtasi (yonida doim matn bo'ladi, faqat rangga tayanilmaydi). */
const Dot = ({ cls }: { cls: string }) => <span className={`dot ${cls}`} aria-hidden="true" />;

function AiCard({ branchId, configured, count }: { branchId?: number; configured: boolean; count: number }) {
  const [state, setState] = useState<{ data?: AiSummary; error?: string; loading?: boolean }>({});

  async function run(refresh = false) {
    setState({ loading: true });
    try {
      const data = await api<AiSummary>(`/insights/recommendations/summary/${qs({ branch: branchId, refresh: refresh ? 1 : undefined })}`,
                                        { method: "POST" });
      setState({ data });
    } catch (err) {
      setState({ error: (err as Error).message });
    }
  }

  return (
    <div className="card stack">
      <div className="spread">
        <h2 className="row gap-2"><Icon name="sparkles" /> AI xulosasi</h2>
        {configured && count > 0 && (
          <button className="btn btn-secondary btn-sm" disabled={state.loading} onClick={() => run(Boolean(state.data))}>
            {state.loading ? "Yozilmoqda..." : state.data ? "Qayta yozdirish" : "Xulosa olish"}
          </button>
        )}
      </div>
      {!configured ? (
        <p className="muted">
          AI xulosasi sozlanmagan. Tavsiyalar baribir to'liq ishlaydi: ularni quyidagi qoidalar chiqaradi.
        </p>
      ) : state.error ? <ErrorBox message={state.error} onRetry={() => run()} /> : state.data ? (
        <>
          <p style={{ whiteSpace: "pre-line", lineHeight: 1.55 }}>{state.data.text}</p>
          <span className="muted">
            Gemini tayyor ro'yxatni umumlashtirdi. Qaysi tovar va necha foiz ekanini qoidalar hisoblagan, AI ularni
            o'zgartirmaydi.
          </span>
        </>
      ) : (
        <p className="muted">
          Gemini quyidagi ro'yxatni o'qib, qaysi tovarlarga birinchi navbatda e'tibor berish kerakligini qisqa yozib beradi.
          Unga faqat tovar nomlari va raqamlar yuboriladi.
        </p>
      )}
    </div>
  );
}

function RecCard({ r, onDismiss }: { r: Recommendation; onDismiss: (r: Recommendation) => void }) {
  const navigate = useNavigate();
  const lv = LEVEL[r.level];

  function createPromotion() {
    const prefill: PromotionPrefill = {
      name: `${r.name}: ${r.discount}% chegirma`, value: String(r.discount),
      products: [{ id: r.product_id, name: r.name }],
    };
    navigate("/promotions", { state: { prefill } });
  }

  return (
    <div className="card stack gap-3">
      <div className="spread" style={{ alignItems: "flex-start" }}>
        <div className="row gap-3 nowrap">
          <ProductThumb src={r.image} size={48} />
          <div>
            <div style={{ fontWeight: 700 }}>{r.name} <span className="muted">· {r.article}</span></div>
            <div className="row gap-2 mt-1">
              <span className={`badge ${lv.badge}`}><Dot cls={lv.dot} /> {r.level_display}</span>
              {r.season_name && <span className="badge badge-neutral">{r.season_name}</span>}
              {r.category_name && <span className="badge badge-neutral">{r.category_name}</span>}
            </div>
          </div>
        </div>
        <div className="right">
          {r.discount > 0
            ? <div className="tile-value">−{r.discount}%</div>
            : <div className="muted">Chegirma imkoni yo'q</div>}
          <div className="muted">tavsiya</div>
        </div>
      </div>

      <div>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>Nega?</div>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {r.reasons.map((t, i) => <li key={i}>{t}</li>)}
        </ul>
      </div>

      <div className="row muted num gap-4">
        <span>Qoldiq: {r.units} dona</span>
        <span>30 kunda sotildi: {r.sold_30} dona</span>
        <span>Tannarxda: {money(r.value_cost)}</span>
        {r.cover_days !== null && <span>Qoldiq {r.cover_days} kunga yetadi</span>}
      </div>

      <div className="row">
        {r.active_promotion ? (
          <span className="badge badge-ok"><Icon name="tag" size={13} /> Faol aksiya bor: {r.active_promotion.label}</span>
        ) : r.can_promote && (
          <button className="btn btn-primary" onClick={createPromotion}><Icon name="tag" size={16} /> Aksiya yaratish (−{r.discount}%)</button>
        )}
        <button className="btn btn-secondary" onClick={() => onDismiss(r)}>Rad etish (30 kun)</button>
      </div>
    </div>
  );
}

const SETTING_ROWS: { label: ReactNode; days: keyof InsightSettings; pct: keyof InsightSettings; hint: string }[] = [
  { label: <><Dot cls="dot-danger" /> Yuqori xavf</>, days: "no_sale_days", pct: "high_discount", hint: "kun bitta ham sotilmasa" },
  { label: <><Dot cls="dot-warn" /> O'rta xavf</>, days: "cover_days_medium", pct: "medium_discount", hint: "kunga yoki undan ko'pga qoldiq yetsa" },
  { label: <><Dot cls="dot-low" /> Past xavf</>, days: "cover_days_low", pct: "low_discount", hint: "kunga yoki undan ko'pga qoldiq yetsa" },
  { label: <><Icon name="leaf" size={15} /> Mavsum</>, days: "season_end_days", pct: "season_discount", hint: "kun ichida mavsum tugasa yoki tugagan bo'lsa" },
];

function SettingsCard({ onSaved }: { onSaved: () => void }) {
  const settings = useAsync(() => api<InsightSettings>("/insights/settings/"), []);
  const [form, setForm] = useState<Record<string, string> | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  if (!settings.data) return settings.error ? <ErrorBox message={settings.error} onRetry={settings.reload} /> : null;
  const value: Record<string, string> = form ?? Object.fromEntries(Object.entries(settings.data).map(([k, v]) => [k, String(v)]));
  const input = (k: keyof InsightSettings) => (
    <input className="input" inputMode="numeric" style={{ width: 80 }} value={value[k]} aria-label={k}
           onChange={(e) => { setForm({ ...value, [k]: e.target.value.replace(/[^\d]/g, "").slice(0, 3) }); setMsg(null); }} />
  );

  async function save(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setFields({});
    try {
      const body = Object.fromEntries(Object.entries(value).map(([k, v]) => [k, Number(v || 0)]));
      settings.setData(await api<InsightSettings>("/insights/settings/", { method: "PATCH", body }));
      setForm(null);
      setMsg("Saqlandi. Tavsiyalar yangilandi.");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    }
  }

  return (
    <form className="card stack" onSubmit={save}>
      <h2>Qoidalar</h2>
      {msg && <Success>{msg}</Success>}
      {error && <ErrorBox message={error} />}
      {SETTING_ROWS.map((row) => (
        <div key={row.days} className="row gap-2">
          <span style={{ minWidth: 120, fontWeight: 600 }}>{row.label}</span>
          {input(row.days)} <span className="muted">{row.hint} →</span> {input(row.pct)} <span className="muted">% chegirma</span>
          {(fields[row.days] || fields[row.pct]) && <span className="field-error">{fields[row.days] || fields[row.pct]}</span>}
        </div>
      ))}
      <Field label="Yangi kelgan tovar necha kun baholanmaydi" error={fields.min_age_days}>
        <div>{input("min_age_days")}</div>
      </Field>
      <p className="muted">
        Bir nechta qoida to'g'ri kelsa, eng katta chegirma olinadi. Chegirma narxni tannarxdan pastga tushirmaydi.
      </p>
      <div><button className="btn btn-primary" disabled={form === null}>Saqlash</button></div>
    </form>
  );
}

export function RecommendationsPage() {
  const { branch, me } = useAuth();
  const multi = (me?.branches.length ?? 0) > 1;
  const [onlyBranch, setOnlyBranch] = useState(false);
  const branchId = onlyBranch ? branch?.id : undefined;
  const [showSettings, setShowSettings] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const list = useAsync(() => api<RecommendationsResponse>(`/insights/recommendations/${qs({ branch: branchId })}`), [branchId]);

  async function dismiss(r: Recommendation) {
    setMessage(null);
    try {
      await api("/insights/recommendations/dismiss/", { method: "POST", body: { product: r.product_id } });
      setMessage(`"${r.name}" 30 kun davomida tavsiyalarda ko'rsatilmaydi.`);
      list.reload();
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  return (
    <div className="stack">
      <PageHeader title="Tavsiyalar">
        <button className="btn btn-secondary btn-sm" onClick={() => setShowSettings((s) => !s)}><Icon name="sliders" size={16} /> Qoidalar</button>
      </PageHeader>
      <p className="muted">
        Sotilmay qolish xavfi bo'lgan tovarlar va ularga tavsiya qilinadigan chegirma. Har bir tavsiyaning sababi ko'rsatilgan.
      </p>
      {multi && (
        <div className="row" role="radiogroup" aria-label="Filiallar">
          <button role="radio" aria-checked={!onlyBranch} className={`chip ${!onlyBranch ? "on" : ""}`} onClick={() => setOnlyBranch(false)}>Barcha filiallar</button>
          <button role="radio" aria-checked={onlyBranch} className={`chip ${onlyBranch ? "on" : ""}`} onClick={() => setOnlyBranch(true)}>{branch?.name}</button>
        </div>
      )}
      {showSettings && <SettingsCard onSaved={list.reload} />}
      {message && <Success>{message}</Success>}

      {list.loading && !list.data ? <Loading /> : list.error || !list.data ? (
        <ErrorBox message={list.error ?? "Xatolik"} onRetry={list.reload} />
      ) : (
        <>
          <div className="tiles">
            <div className="card tile"><span className="muted">Xavf ostidagi tovarlar</span><span className="tile-value">{list.data.summary.count}</span></div>
            <div className="card tile"><span className="muted"><Dot cls="dot-danger" /> Yuqori / <Dot cls="dot-warn" /> O'rta / <Dot cls="dot-low" /> Past</span>
              <span className="tile-value">{list.data.summary.high} / {list.data.summary.medium} / {list.data.summary.low}</span></div>
            <div className="card tile"><span className="muted">Omborda muzlab turgan pul (tannarxda)</span>
              <span className="tile-value tile-warn">{money(list.data.summary.frozen_value)}</span></div>
          </div>
          <AiCard key={branchId ?? "all"} branchId={branchId} configured={list.data.ai_configured} count={list.data.summary.count} />
          {list.data.results.length === 0 ? (
            <Empty title="Xavf ostidagi tovar yo'q" hint="Hamma tovarlar me'yorida sotilmoqda." />
          ) : list.data.results.map((r) => <RecCard key={r.product_id} r={r} onDismiss={dismiss} />)}
        </>
      )}
    </div>
  );
}
