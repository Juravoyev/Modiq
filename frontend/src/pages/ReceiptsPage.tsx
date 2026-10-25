import { useState } from "react";

import { api, ApiError, qs } from "../api/client";
import type { Page, Variant } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorBox, Field, Loading, Pagination, Success } from "../components/ui";
import { dateTime, money } from "../utils/format";
import { useAsync, useDebounced } from "../utils/useAsync";

interface ReceiptLine { id?: number; variant: number; sku: string; variant_name: string; quantity: number; purchase_price: string }
interface Receipt {
  id: number; branch: number; branch_name: string; supplier_name: string; document_number: string; document_date: string;
  status: "draft" | "confirmed" | "cancelled"; lines: ReceiptLine[]; total_quantity: number; total_cost: string; created_at: string;
}

const STATUS: Record<Receipt["status"], { label: string; cls: string; icon: string }> = {
  draft: { label: "Qoralama", cls: "badge-neutral", icon: "○" },
  confirmed: { label: "Tasdiqlangan", cls: "badge-ok", icon: "✓" },
  cancelled: { label: "Bekor qilingan", cls: "badge-danger", icon: "✕" },
};

const today = () => new Date().toISOString().slice(0, 10);

function NewReceipt({ onSaved }: { onSaved: (r: Receipt) => void }) {
  const { branch } = useAuth();
  const [head, setHead] = useState({ supplier_name: "", document_number: "", document_date: today() });
  const [lines, setLines] = useState<ReceiptLine[]>([]);
  const [query, setQuery] = useState("");
  const search = useDebounced(query.trim());
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const results = useAsync(
    () => (search ? api<Page<Variant>>(`/catalog/variants/${qs({ search, branch: branch?.id })}`) : Promise.resolve(null)),
    [search, branch?.id],
  );

  function add(v: Variant) {
    if (!lines.some((l) => l.variant === v.id)) {
      setLines([...lines, { variant: v.id, sku: v.sku, variant_name: `${v.product_name} / ${v.color_name} / ${v.size_name}`,
                            quantity: 1, purchase_price: v.effective_purchase_price }]);
    }
    setQuery("");
  }
  const update = (id: number, patch: Partial<ReceiptLine>) => setLines(lines.map((l) => (l.variant === id ? { ...l, ...patch } : l)));

  async function save(confirm: boolean) {
    if (!branch) return;
    setBusy(true);
    setError(null);
    setFields({});
    try {
      let r = await api<Receipt>("/inventory/receipts/", {
        method: "POST",
        body: { ...head, branch: branch.id, lines: lines.map(({ variant, quantity, purchase_price }) => ({ variant, quantity, purchase_price })) },
      });
      if (confirm) r = await api<Receipt>(`/inventory/receipts/${r.id}/confirm/`, { method: "POST" });
      onSaved(r);
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  const total = lines.reduce((s, l) => s + l.quantity * Number(l.purchase_price || 0), 0);

  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>Yangi kirim · {branch?.name}</h2>
      {error && <ErrorBox message={error} />}
      <div className="grid-2">
        <Field label="Yetkazib beruvchi" error={fields.supplier_name}>
          <input className="input" value={head.supplier_name} onChange={(e) => setHead({ ...head, supplier_name: e.target.value })} />
        </Field>
        <Field label="Hujjat raqami" error={fields.document_number}>
          <input className="input" value={head.document_number} onChange={(e) => setHead({ ...head, document_number: e.target.value })} />
        </Field>
        <Field label="Sana" error={fields.document_date}>
          <input className="input" type="date" value={head.document_date} onChange={(e) => setHead({ ...head, document_date: e.target.value })} />
        </Field>
      </div>
      <Field label="Tovar qo'shish" error={fields.lines}>
        <input className="input" type="search" placeholder="SKU yoki tovar nomi" value={query} onChange={(e) => setQuery(e.target.value)} />
      </Field>
      {search && (results.loading ? <Loading text="Qidirilmoqda..." /> : (
        <div className="stack" style={{ gap: 6 }}>
          {results.data?.results.map((v) => (
            <button key={v.id} className="result-item" onClick={() => add(v)}>
              <span>{v.product_name} · {v.color_name} · {v.size_name}</span><span className="muted">{v.sku}</span>
            </button>
          ))}
          {results.data && !results.data.results.length && <span className="muted">Topilmadi</span>}
        </div>
      ))}
      {lines.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Variant</th><th>Miqdor</th><th>Xarid narxi</th><th className="right">Summa</th><th /></tr></thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.variant}>
                  <td>{l.variant_name}<div className="muted">{l.sku}</div></td>
                  <td style={{ width: 100 }}>
                    <input className="input" inputMode="numeric" value={l.quantity}
                           onChange={(e) => update(l.variant, { quantity: Math.max(1, Number(e.target.value.replace(/\D/g, "")) || 1) })} />
                  </td>
                  <td style={{ width: 150 }}>
                    <input className="input" inputMode="decimal" value={l.purchase_price}
                           onChange={(e) => update(l.variant, { purchase_price: e.target.value.replace(/[^\d.]/g, "") })} />
                  </td>
                  <td className="right num">{money(l.quantity * Number(l.purchase_price || 0))}</td>
                  <td><button className="btn btn-secondary btn-sm" aria-label="O'chirish"
                              onClick={() => setLines(lines.filter((x) => x.variant !== l.variant))}>✕</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="spread">
        <span className="num"><b>Jami: {money(total)}</b> · {lines.reduce((s, l) => s + l.quantity, 0)} dona</span>
        <div className="row">
          <button className="btn btn-secondary" disabled={busy || !lines.length} onClick={() => save(false)}>Qoralama saqlash</button>
          <button className="btn btn-primary" disabled={busy || !lines.length} onClick={() => save(true)}>Saqlash va tasdiqlash</button>
        </div>
      </div>
      <p className="muted" style={{ margin: 0 }}>Qoldiq faqat kirim tasdiqlanganda oshadi. Tasdiqlangan kirimni o'zgartirib bo'lmaydi.</p>
    </div>
  );
}

export function ReceiptsPage() {
  const { branch, isManager } = useAuth();
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const list = useAsync(() => api<Page<Receipt>>(`/inventory/receipts/${qs({ page })}`), [page, branch?.id]);

  async function confirm(id: number) {
    setActionError(null);
    try {
      await api(`/inventory/receipts/${id}/confirm/`, { method: "POST" });
      setMessage("Kirim tasdiqlandi, qoldiq yangilandi.");
      list.reload();
    } catch (e) {
      setActionError((e as Error).message);
    }
  }

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Kirim</h1>
        {isManager && !creating && <button className="btn btn-primary" onClick={() => { setCreating(true); setMessage(null); }}>+ Yangi kirim</button>}
      </div>
      {!isManager && <div className="alert alert-warn">Kirimni faqat menejer yoki do'kon egasi kiritadi.</div>}
      {message && <Success>{message}</Success>}
      {actionError && <ErrorBox message={actionError} />}
      {creating && (
        <NewReceipt onSaved={(r) => {
          setCreating(false);
          setMessage(r.status === "confirmed" ? "Kirim tasdiqlandi, qoldiq yangilandi." : "Kirim qoralama sifatida saqlandi.");
          list.reload();
        }} />
      )}
      <div className="card" style={{ padding: 0 }}>
        {list.loading ? <Loading /> : list.error ? <div style={{ padding: 16 }}><ErrorBox message={list.error} onRetry={list.reload} /></div> :
          !list.data?.results.length ? <Empty title="Hali kirim yo'q" hint="Yetkazib beruvchidan kelgan tovarni shu yerda kiriting." /> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>№</th><th>Sana</th><th>Filial</th><th>Yetkazib beruvchi</th><th className="right">Miqdor</th><th className="right">Summa</th><th>Holat</th><th /></tr></thead>
                <tbody>
                  {list.data.results.map((r) => (
                    <tr key={r.id}>
                      <td>{r.id}{r.document_number && <div className="muted">{r.document_number}</div>}</td>
                      <td>{r.document_date}<div className="muted">{dateTime(r.created_at)}</div></td>
                      <td>{r.branch_name}</td>
                      <td>{r.supplier_name || "—"}</td>
                      <td className="right num">{r.total_quantity}</td>
                      <td className="right num">{money(r.total_cost)}</td>
                      <td><span className={`badge ${STATUS[r.status].cls}`}>{STATUS[r.status].icon} {STATUS[r.status].label}</span></td>
                      <td>{isManager && r.status === "draft" && <button className="btn btn-primary btn-sm" onClick={() => confirm(r.id)}>Tasdiqlash</button>}</td>
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
