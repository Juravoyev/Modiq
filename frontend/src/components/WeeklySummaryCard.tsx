import { useState } from "react";

import { api, qs } from "../api/client";
import type { WeeklySummary } from "../api/types";
import { dateTime, money } from "../utils/format";
import { useAsync } from "../utils/useAsync";
import { ErrorBox, Loading } from "./ui";

/** Haftalik xulosa: raqamlar tizimdan, matn shu raqamlar asosida avtomatik yoziladi. */
export function WeeklySummaryCard({ branchId }: { branchId?: number }) {
  const base = useAsync(() => api<WeeklySummary>(`/reports/weekly-summary/${qs({ branch: branchId })}`), [branchId]);
  const [result, setResult] = useState<WeeklySummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate(refresh: boolean) {
    setBusy(true);
    setError(null);
    try {
      setResult(await api<WeeklySummary>(`/reports/weekly-summary/${qs({ branch: branchId })}`, {
        method: "POST", body: { refresh },
      }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (base.loading) return <div className="card"><Loading /></div>;
  if (base.error || !base.data) return <ErrorBox message={base.error ?? "Xatolik"} onRetry={base.reload} />;
  const f = (result ?? base.data).facts;
  const now = Number(f.shu_hafta.revenue);
  const before = Number(f.oldingi_hafta.revenue);

  return (
    <div className="card stack" style={{ gap: 10 }}>
      <div className="spread">
        <h2 style={{ margin: 0 }}>Haftalik xulosa</h2>
        <span className="muted">{f.davr}</span>
      </div>
      <div className="facts">
        <span>Tushum: <b>{money(now)}</b></span>
        <span>Oldingi hafta: <b>{money(before)}</b></span>
        <span>Cheklar: <b>{f.shu_hafta.sales_count}</b></span>
        <span>Taxminiy yalpi foyda: <b>{money(f.shu_hafta.gross_profit)}</b></span>
        <span>Amaldagi chegirmalar: <b>{f.amaldagi_chegirmalar}</b></span>
      </div>
      {result?.text && (
        <div className="why-body" style={{ whiteSpace: "pre-line" }}>{result.text}</div>
      )}
      {error && <ErrorBox message={error} />}
      {base.data.configured === false && !result && !error && (
        <p className="muted" style={{ margin: 0 }}>
          Matnli xulosa uchun backend/.env faylida GEMINI_API_KEY ko'rsatilishi kerak. Raqamlar baribir yuqorida.
        </p>
      )}
      <div className="row" style={{ gap: 8 }}>
        <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => generate(Boolean(result))}>
          {busy ? "Tayyorlanmoqda..." : result?.text ? "Qayta tayyorlash" : "Xulosa tayyorlash"}
        </button>
        {result?.generated_at && <span className="muted">Tayyorlandi: {dateTime(result.generated_at)}{result.cached ? " (saqlangan)" : ""}</span>}
      </div>
      <p className="muted" style={{ margin: 0, fontSize: 12 }}>
        Matn tizim hisoblagan raqamlar asosida avtomatik yoziladi va xato bo'lishi mumkin. Qaror qabul qilishdan oldin
        Hisobotlar sahifasida tekshiring.
      </p>
    </div>
  );
}
