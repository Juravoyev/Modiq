import { useState } from "react";

import { api, ApiError, qs } from "../api/client";
import type { Page, ReturnStatus, Sale, SaleReturn } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorBox, Field, Loading, Pagination, Success } from "../components/ui";
import { dateTime, money } from "../utils/format";
import { useAsync } from "../utils/useAsync";

const STATUS: Record<ReturnStatus, { cls: string; icon: string }> = {
  pending: { cls: "badge-warn", icon: "◷" },
  approved: { cls: "badge-ok", icon: "✓" },
  rejected: { cls: "badge-danger", icon: "✕" },
};

export function ReturnBadge({ r }: { r: Pick<SaleReturn, "status" | "status_display"> }) {
  return <span className={`badge ${STATUS[r.status].cls}`}>{STATUS[r.status].icon} {r.status_display}</span>;
}

/** Savdo chekidan yaroqsiz tovarni qaytarish. Sotuvdan 24 soat o'tgach yopiladi. */
export function ReturnForm({ sale, onDone, onCancel }: { sale: Sale; onDone: (r: SaleReturn) => void; onCancel: () => void }) {
  const [qty, setQty] = useState<Record<number, number>>({});
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const lines = sale.lines.map((l) => ({ ...l, left: l.quantity - l.returned_quantity }));
  const chosen = lines.filter((l) => (qty[l.id] ?? 0) > 0);
  const refund = chosen.reduce((s, l) => s + (Number(l.line_total) * qty[l.id]) / l.quantity, 0);

  async function submit() {
    setBusy(true);
    setError(null);
    setFields({});
    try {
      onDone(await api<SaleReturn>("/sales/returns/", {
        method: "POST",
        body: { sale: sale.id, reason, lines: chosen.map((l) => ({ sale_line: l.id, quantity: qty[l.id] })) },
      }));
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card stack no-print">
      <h2 style={{ margin: 0 }}>Yaroqsiz tovarni qaytarish</h2>
      <p className="muted" style={{ margin: 0 }}>
        Faqat yaroqsiz tovar qaytariladi. Qaytarilgan tovar sotuvga qaytmaydi, hisobdan chiqariladi.
        Muddat: {dateTime(sale.return_deadline)} gacha.
      </p>
      {error && <ErrorBox message={error} />}
      {lines.map((l) => (
        <div key={l.id} className="spread">
          <div>
            <div>{l.variant_name}</div>
            <div className="muted">{l.quantity} dona sotilgan{l.returned_quantity > 0 && `, ${l.returned_quantity} dona qaytarilgan`}</div>
          </div>
          {l.left > 0 ? (
            <div className="qty">
              <button onClick={() => setQty({ ...qty, [l.id]: Math.max(0, (qty[l.id] ?? 0) - 1) })} aria-label="Kamaytirish">−</button>
              <span className="num">{qty[l.id] ?? 0}</span>
              <button onClick={() => setQty({ ...qty, [l.id]: Math.min(l.left, (qty[l.id] ?? 0) + 1) })} aria-label="Ko'paytirish"
                      disabled={(qty[l.id] ?? 0) >= l.left}>+</button>
            </div>
          ) : <span className="muted">Qaytarilgan</span>}
        </div>
      ))}
      <Field label="Yaroqsizlik sababi *" error={fields.reason}>
        <input className="input" value={reason} placeholder="Masalan: choki so'kilgan, dog' bor" onChange={(e) => setReason(e.target.value)} />
      </Field>
      <div className="total-row big num"><span>Mijozga qaytariladi</span><span>{money(refund)}</span></div>
      <div className="row">
        <button className="btn btn-secondary" onClick={onCancel}>Bekor qilish</button>
        <button className="btn btn-primary" disabled={busy || !chosen.length || !reason.trim()} onClick={submit}>
          {busy ? "Yuborilmoqda..." : "Qaytarish"}
        </button>
      </div>
    </div>
  );
}

export function ReturnsPage() {
  const { branch, me, isManager } = useAuth();
  const [status, setStatus] = useState<ReturnStatus | "">("pending");
  const [page, setPage] = useState(1);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const list = useAsync(
    () => api<Page<SaleReturn>>(`/sales/returns/${qs({ branch: branch?.id, status, page })}`),
    [branch?.id, status, page],
  );
  const canDecide = !!me?.can_approve_returns;

  async function decide(r: SaleReturn, approve: boolean) {
    let note = "";
    if (!approve) {
      const answer = window.prompt("Rad etish sababi (ixtiyoriy):", "");
      if (answer === null) return;
      note = answer;
    }
    setBusy(true);
    setActionError(null);
    setMessage(null);
    try {
      await api(`/sales/returns/${r.id}/${approve ? "approve" : "reject"}/`, { method: "POST", body: { note } });
      setMessage(approve ? `Tasdiqlandi. Mijozga ${money(r.refund_total)} qaytaring.` : "Qaytarish rad etildi.");
      list.reload();
    } catch (e) {
      setActionError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const filters: { value: ReturnStatus | ""; label: string }[] = [
    { value: "pending", label: "Tasdiq kutilmoqda" }, { value: "approved", label: "Tasdiqlangan" },
    { value: "rejected", label: "Rad etilgan" }, { value: "", label: "Barchasi" },
  ];

  return (
    <div className="stack">
      <h1>Qaytarish · {branch?.name}</h1>
      <p className="muted" style={{ margin: 0 }}>
        Yangi qaytarish "Savdolar" bo'limida chekni ochib qilinadi.
        {!canDecide && " Sizning so'rovingizni mas'ul xodim tasdiqlagach, mijozga pulni qaytarasiz."}
      </p>
      <div className="row" role="radiogroup" aria-label="Holat">
        {filters.map((f) => (
          <button key={f.value} role="radio" aria-checked={status === f.value} className={`chip ${status === f.value ? "on" : ""}`}
                  onClick={() => { setStatus(f.value); setPage(1); }}>{f.label}</button>
        ))}
      </div>
      {message && <Success>{message}</Success>}
      {actionError && <ErrorBox message={actionError} />}
      <div className="card" style={{ padding: 0 }}>
        {list.loading ? <Loading /> : list.error ? <div style={{ padding: 16 }}><ErrorBox message={list.error} onRetry={list.reload} /></div> :
          !list.data?.results.length ? <Empty title="Qaytarish yo'q" /> : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>№</th><th>Vaqt</th><th>Tovar va sabab</th><th className="right">Qaytariladi</th>
                    {isManager && <th className="right">Zarar (tannarx)</th>}<th>Holat</th><th />
                  </tr>
                </thead>
                <tbody>
                  {list.data.results.map((r) => (
                    <tr key={r.id}>
                      <td>{r.id}<div className="muted">Chek № {r.sale}</div></td>
                      <td>{dateTime(r.created_at)}<div className="muted">{r.requested_by_name}</div></td>
                      <td>
                        {r.lines.map((l) => <div key={l.id}>{l.variant_name} × {l.quantity}</div>)}
                        <div className="muted">Sabab: {r.reason}</div>
                        {r.decision_note && <div className="muted">Izoh: {r.decision_note}</div>}
                      </td>
                      <td className="right num"><b>{money(r.refund_total)}</b></td>
                      {isManager && <td className="right num">{money(r.cost_total)}</td>}
                      <td><ReturnBadge r={r} />{r.decided_by_name && <div className="muted">{r.decided_by_name}</div>}</td>
                      <td>
                        {canDecide && r.status === "pending" && (
                          <div className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
                            <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => decide(r, true)}>Tasdiqlash</button>
                            <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => decide(r, false)}>Rad etish</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>
      {list.data && <Pagination page={page} count={list.data.count} onChange={setPage} />}
    </div>
  );
}
