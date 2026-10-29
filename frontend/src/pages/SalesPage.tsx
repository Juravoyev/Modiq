import { useState } from "react";

import { api, qs } from "../api/client";
import type { Page, Sale } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Receipt } from "../components/Receipt";
import { Empty, ErrorBox, Loading, Pagination, Success } from "../components/ui";
import { dateTime, money } from "../utils/format";
import { useAsync } from "../utils/useAsync";
import { ReturnForm } from "./ReturnsPage";

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
    const canReturn = new Date(selected.return_deadline) > new Date() &&
      selected.lines.some((l) => l.quantity > l.returned_quantity);
    return (
      <div className="stack" style={{ maxWidth: 420, margin: "0 auto" }}>
        <button className="btn btn-secondary no-print" onClick={() => { setSelected(null); setReturning(false); setNotice(null); reload(); }}>
          ‹ Savdolar ro'yxati
        </button>
        {notice && <div className="no-print"><Success>{notice}</Success></div>}
        <div className="card"><Receipt sale={selected} businessName={me?.business.name ?? ""} /></div>
        {returning ? (
          <ReturnForm sale={selected} onCancel={() => setReturning(false)} onDone={async (r) => {
            setReturning(false);
            setNotice(r.status === "approved"
              ? `Qaytarish tasdiqlandi. Mijozga ${money(r.refund_total)} qaytaring.`
              : "So'rov yuborildi. Mas'ul xodim tasdiqlagach, mijozga pulni qaytaring (\"Qaytarish\" bo'limi).");
            setSelected(await api<Sale>(`/sales/${selected.id}/`));
          }} />
        ) : canReturn && (
          <button className="btn btn-secondary no-print" onClick={() => { setReturning(true); setNotice(null); }}>
            ↩ Yaroqsiz tovarni qaytarish
          </button>
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
                      <td className="right num"><b>{money(s.total)}</b></td>
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
