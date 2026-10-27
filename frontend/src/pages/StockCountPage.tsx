import { useState } from "react";

import { api, qs } from "../api/client";
import type { Page, StockCount, StockRow } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { DocStatusBadge } from "../components/StatusBadge";
import { VariantPicker } from "../components/VariantPicker";
import { Empty, ErrorBox, Loading, Pagination, Success } from "../components/ui";
import { dateTime } from "../utils/format";
import { useAsync } from "../utils/useAsync";

interface Line { variant: number; sku: string; variant_name: string; system: number; counted: string }

function NewCount({ onSaved }: { onSaved: (c: StockCount) => void }) {
  const { branch } = useAuth();
  const [lines, setLines] = useState<Line[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadAll() {
    setError(null);
    try {
      const rows = await api<Page<StockRow>>(`/inventory/stock/${qs({ branch: branch?.id, page_size: 200 })}`);
      setLines(rows.results.map((r) => ({ variant: r.variant, sku: r.sku, variant_name: r.variant_name, system: r.quantity, counted: "" })));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function save(apply: boolean) {
    if (!branch) return;
    const filled = lines.filter((l) => l.counted !== "");
    if (!filled.length) return setError("Kamida bitta variantning sanog'ini kiriting.");
    setBusy(true);
    setError(null);
    try {
      let c = await api<StockCount>("/inventory/counts/", {
        method: "POST",
        body: { branch: branch.id, note, lines: filled.map((l) => ({ variant: l.variant, counted_quantity: Number(l.counted) })) },
      });
      if (apply) c = await api<StockCount>(`/inventory/counts/${c.id}/apply/`, { method: "POST" });
      onSaved(c);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const filled = lines.filter((l) => l.counted !== "");
  const diff = filled.reduce((s, l) => s + (Number(l.counted) - l.system), 0);

  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>Yangi inventarizatsiya · {branch?.name}</h2>
      {error && <ErrorBox message={error} />}
      <div className="row">
        <button className="btn btn-secondary" onClick={loadAll}>Filialdagi barcha variantlarni yuklash</button>
        <span className="muted">yoki tovarlarni birma-bir qo'shing</span>
      </div>
      <VariantPicker branchId={branch?.id} onPick={(v) => {
        if (!lines.some((l) => l.variant === v.id)) {
          setLines([...lines, { variant: v.id, sku: v.sku, variant_name: `${v.product_name} / ${v.color_name} / ${v.size_name}`,
                                system: v.stock ?? 0, counted: "" }]);
        }
      }} />
      <label className="field"><span className="field-label">Izoh</span>
        <input className="input" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Masalan: oylik sanoq" />
      </label>
      {lines.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Variant</th><th className="right">Tizimda</th><th>Sanoqda</th><th className="right">Farq</th></tr></thead>
            <tbody>
              {lines.map((l) => {
                const d = l.counted === "" ? null : Number(l.counted) - l.system;
                return (
                  <tr key={l.variant}>
                    <td>{l.variant_name}<div className="muted">{l.sku}</div></td>
                    <td className="right num">{l.system}</td>
                    <td style={{ width: 110 }}>
                      <input className="input" inputMode="numeric" value={l.counted} placeholder="—"
                             onChange={(e) => setLines(lines.map((x) => x.variant === l.variant ? { ...x, counted: e.target.value.replace(/\D/g, "") } : x))} />
                    </td>
                    <td className="right num">
                      {d === null ? <span className="muted">—</span> : d === 0 ? <span className="badge badge-ok">● 0</span>
                        : d < 0 ? <span className="badge badge-danger">▼ {d}</span> : <span className="badge badge-warn">▲ +{d}</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <div className="spread">
        <span className="muted">Sanalgan: {filled.length} variant · umumiy farq: {diff > 0 ? `+${diff}` : diff} dona</span>
        <div className="row">
          <button className="btn btn-secondary" disabled={busy} onClick={() => save(false)}>Qoralama saqlash</button>
          <button className="btn btn-primary" disabled={busy} onClick={() => save(true)}>Tasdiqlash va qoldiqni tuzatish</button>
        </div>
      </div>
      <p className="muted" style={{ margin: 0 }}>Faqat sanoq kiritilgan variantlar tuzatiladi. Har bir farq ombor harakatlari tarixida saqlanadi.</p>
    </div>
  );
}

export function StockCountPage() {
  const { branch, isManager } = useAuth();
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const list = useAsync(() => api<Page<StockCount>>(`/inventory/counts/${qs({ page })}`), [page, branch?.id]);

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Inventarizatsiya</h1>
        {isManager && !creating && <button className="btn btn-primary" onClick={() => { setCreating(true); setMessage(null); }}>+ Yangi sanoq</button>}
      </div>
      {!isManager && <div className="alert alert-warn">Inventarizatsiyani menejer yoki do'kon egasi o'tkazadi.</div>}
      {message && <Success>{message}</Success>}
      {creating && <NewCount onSaved={(c) => {
        setCreating(false);
        setMessage(c.status === "applied" ? `Qoldiq tuzatildi. Kamomad: ${c.shortage} dona, ortiqcha: ${c.surplus} dona.` : "Qoralama saqlandi.");
        list.reload();
      }} />}
      <div className="card" style={{ padding: 0 }}>
        {list.loading ? <Loading /> : list.error ? <div style={{ padding: 16 }}><ErrorBox message={list.error} onRetry={list.reload} /></div> :
          !list.data?.results.length ? <Empty title="Hali inventarizatsiya o'tkazilmagan" /> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>№</th><th>Sana</th><th>Filial</th><th className="right">Variantlar</th><th className="right">Kamomad</th><th className="right">Ortiqcha</th><th>Holat</th><th /></tr></thead>
                <tbody>
                  {list.data.results.map((c) => (
                    <tr key={c.id}>
                      <td>{c.id}</td>
                      <td>{dateTime(c.created_at)}{c.note && <div className="muted">{c.note}</div>}</td>
                      <td>{c.branch_name}</td>
                      <td className="right num">{c.lines.length}</td>
                      <td className="right num">{c.status === "applied" ? c.shortage : "—"}</td>
                      <td className="right num">{c.status === "applied" ? c.surplus : "—"}</td>
                      <td><DocStatusBadge status={c.status} /></td>
                      <td>{isManager && c.status === "draft" && (
                        <button className="btn btn-primary btn-sm" onClick={async () => {
                          try {
                            const r = await api<StockCount>(`/inventory/counts/${c.id}/apply/`, { method: "POST" });
                            setMessage(`Qoldiq tuzatildi. Kamomad: ${r.shortage} dona, ortiqcha: ${r.surplus} dona.`);
                            list.reload();
                          } catch (e) { setMessage((e as Error).message); }
                        }}>Tasdiqlash</button>
                      )}</td>
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
