import { useState } from "react";

import { api, qs } from "../api/client";
import type { Page, Sale } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Receipt } from "../components/Receipt";
import { Empty, ErrorBox, Field, Loading, Pagination, Success } from "../components/ui";
import { dateTime, money } from "../utils/format";
import { useAsync } from "../utils/useAsync";

function ReturnForm({ sale, onDone }: { sale: Sale; onDone: (updated: Sale) => void }) {
  const [qty, setQty] = useState<Record<number, string>>({});
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const lines = sale.lines.filter((l) => l.quantity - l.returned_quantity > 0);

  async function submit() {
    const items = Object.entries(qty).filter(([, q]) => Number(q) > 0).map(([id, q]) => ({ sale_line: Number(id), quantity: Number(q) }));
    if (!items.length) return setError("Qaytariladigan miqdorni kiriting.");
    setBusy(true);
    setError(null);
    try {
      await api(`/sales/${sale.id}/return/`, { method: "POST", body: { lines: items, reason } });
      onDone(await api<Sale>(`/sales/${sale.id}/`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!lines.length) return <p className="muted">Bu savdodagi barcha tovarlar qaytarilgan.</p>;
  return (
    <div className="card stack no-print">
      <h2 style={{ margin: 0 }}>Tovarni qaytarish</h2>
      {error && <ErrorBox message={error} />}
      {lines.map((l) => {
        const left = l.quantity - l.returned_quantity;
        return (
          <div key={l.id} className="spread">
            <span>{l.variant_name}<div className="muted">Qaytarish mumkin: {left} dona · 1 dona = {money(Number(l.line_total) / l.quantity)}</div></span>
            <input className="input" style={{ width: 80 }} inputMode="numeric" placeholder="0" value={qty[l.id] ?? ""}
                   aria-label={`${l.sku} qaytariladigan miqdor`}
                   onChange={(e) => setQty({ ...qty, [l.id]: String(Math.min(left, Number(e.target.value.replace(/\D/g, "")) || 0) || "") })} />
          </div>
        );
      })}
      <Field label="Sabab"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Masalan: o'lcham to'g'ri kelmadi" /></Field>
      <button className="btn btn-primary" disabled={busy} onClick={submit}>{busy ? "Bajarilmoqda..." : "Qaytarishni tasdiqlash"}</button>
      <p className="muted" style={{ margin: 0 }}>Qaytarilgan tovar qoldiqqa qo'shiladi, summasi bugungi tushumdan ayiriladi.</p>
    </div>
  );
}

export function SalesPage() {
  const { branch, me, isManager } = useAuth();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Sale | null>(null);
  const [returning, setReturning] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const { data, error, loading, reload } = useAsync(
    () => api<Page<Sale>>(`/sales/${qs({ branch: branch?.id, page })}`),
    [branch?.id, page],
  );

  if (selected) {
    return (
      <div className="stack" style={{ maxWidth: 420, margin: "0 auto" }}>
        <button className="btn btn-secondary no-print" onClick={() => { setSelected(null); setReturning(false); setNotice(null); reload(); }}>‹ Savdolar ro'yxati</button>
        {notice && <Success>{notice}</Success>}
        <div className="card"><Receipt sale={selected} businessName={me?.business.name ?? ""} /></div>
        {selected.returns.length > 0 && (
          <div className="card no-print">
            <h3>Qaytarishlar</h3>
            {selected.returns.map((r) => (
              <div key={r.id} className="list-row">
                <span>{dateTime(r.created_at)}{r.reason && <div className="muted">{r.reason}</div>}</span>
                <b className="num">−{money(r.refund_total)}</b>
              </div>
            ))}
          </div>
        )}
        {returning ? (
          <ReturnForm sale={selected} onDone={(s) => { setSelected(s); setReturning(false); setNotice("Qaytarish bajarildi, qoldiq tiklandi."); }} />
        ) : (
          <button className="btn btn-secondary no-print" onClick={() => setReturning(true)}>↩ Tovarni qaytarish</button>
        )}
        {isManager && selected.gross_profit !== undefined && (
          <div className="card no-print">
            <div className="total-row num"><span>Tannarx</span><span>{money(selected.cost_total)}</span></div>
            <div className="total-row num"><span>Taxminiy yalpi foyda</span><span>{money(selected.gross_profit)}</span></div>
            <p className="muted" style={{ margin: "6px 0 0" }}>Ijara, maosh va boshqa xarajatlar hisobga olinmagan, bu sof foyda emas.</p>
          </div>
        )}
        <button className="btn btn-secondary no-print" onClick={() => window.print()}>Chop etish</button>
      </div>
    );
  }

  return (
    <div className="stack">
      <h1>Savdolar · {branch?.name}</h1>
      <div className="card" style={{ padding: 0 }}>
        {loading ? <Loading /> : error ? <div style={{ padding: 16 }}><ErrorBox message={error} onRetry={reload} /></div> :
          !data?.results.length ? <Empty title="Hali savdo yo'q" hint="Kassa sahifasida birinchi savdoni qiling." /> : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Chek</th><th>Vaqt</th><th>Sotuvchi</th><th>To'lov</th><th className="right">Tovar</th>
                    <th className="right">Jami</th>{isManager && <th className="right">Taxminiy yalpi foyda</th>}
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((s) => (
                    <tr key={s.id} style={{ cursor: "pointer" }} onClick={() => setSelected(s)}>
                      <td>№ {s.id}</td>
                      <td>{dateTime(s.created_at)}</td>
                      <td>{s.cashier_name || "—"}</td>
                      <td>{s.payment_type_display}</td>
                      <td className="right num">{s.lines.reduce((n, l) => n + l.quantity, 0)}</td>
                      <td className="right num"><b>{money(s.total)}</b>
                        {Number(s.returned_total) > 0 && <div className="badge badge-warn">↩ −{money(s.returned_total)}</div>}</td>
                      {isManager && <td className="right num">{money(s.gross_profit)}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  );
}
