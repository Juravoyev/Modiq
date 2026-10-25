import { useState } from "react";

import { api, qs } from "../api/client";
import type { Page, StockRow } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorBox, Loading, Pagination, StockBadge } from "../components/ui";
import { dateTime } from "../utils/format";
import { useAsync, useDebounced } from "../utils/useAsync";

export function StockPage() {
  const { branch } = useAuth();
  const [query, setQuery] = useState("");
  const search = useDebounced(query.trim());
  const [low, setLow] = useState(false);
  const [page, setPage] = useState(1);
  const { data, error, loading, reload } = useAsync(
    () => api<Page<StockRow>>(`/inventory/stock/${qs({ branch: branch?.id, search, low: low || undefined, page })}`),
    [branch?.id, search, low, page],
  );

  return (
    <div className="stack">
      <h1>Qoldiq · {branch?.name}</h1>
      <div className="row">
        <input className="input" style={{ flex: 1, minWidth: 200 }} type="search" placeholder="SKU yoki tovar nomi"
               value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} />
        <button className={`chip ${low ? "on" : ""}`} aria-pressed={low} onClick={() => { setLow(!low); setPage(1); }}>
          ▲ Faqat kam qolganlar
        </button>
      </div>
      <div className="card" style={{ padding: 0 }}>
        {loading ? <Loading /> : error ? <div style={{ padding: 16 }}><ErrorBox message={error} onRetry={reload} /></div> :
          !data?.results.length ? (
            <Empty title={low ? "Kam qolgan tovar yo'q" : "Qoldiq yo'q"} hint={low ? undefined : "Qoldiq kirim tasdiqlangandan keyin paydo bo'ladi."} />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Variant</th><th>SKU</th><th className="right">Qoldiq</th><th className="right">Minimal</th><th>Holat</th><th>Yangilangan</th></tr></thead>
                <tbody>
                  {data.results.map((s) => (
                    <tr key={s.id}>
                      <td>{s.variant_name}</td>
                      <td>{s.sku}</td>
                      <td className="right num"><b>{s.quantity}</b></td>
                      <td className="right num">{s.min_stock}</td>
                      <td><StockBadge quantity={s.quantity} min={s.min_stock} /></td>
                      <td className="muted">{dateTime(s.updated_at)}</td>
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
