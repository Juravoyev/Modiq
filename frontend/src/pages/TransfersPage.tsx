import { useState } from "react";

import { api, ApiError, qs } from "../api/client";
import type { Branch, Page, Transfer } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { DocStatusBadge } from "../components/StatusBadge";
import { VariantPicker } from "../components/VariantPicker";
import { Empty, ErrorBox, Field, Loading, Pagination, Success } from "../components/ui";
import { dateTime } from "../utils/format";
import { useAsync } from "../utils/useAsync";

type Line = Transfer["lines"][number] & { available: number };

function NewTransfer({ onSaved }: { onSaved: (t: Transfer) => void }) {
  const { branch, me } = useAuth();
  const all = useAsync(() => api<Page<Branch>>("/auth/branches/?page_size=100"), []);
  const targets = (all.data?.results ?? me?.branches ?? []).filter((b) => b.id !== branch?.id);
  const [to, setTo] = useState<number | "">("");
  const [note, setNote] = useState("");
  const [lines, setLines] = useState<Line[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save(send: boolean) {
    if (!branch || !to) return setError("Qabul qiluvchi filialni tanlang.");
    setBusy(true);
    setError(null);
    try {
      let t = await api<Transfer>("/inventory/transfers/", {
        method: "POST",
        body: { from_branch: branch.id, to_branch: to, note, lines: lines.map(({ variant, quantity }) => ({ variant, quantity })) },
      });
      if (send) t = await api<Transfer>(`/inventory/transfers/${t.id}/send/`, { method: "POST" });
      onSaved(t);
    } catch (e) {
      const err = e as ApiError;
      setError([err.message, ...Object.values(err.fields ?? {})].join(" "));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>Yangi ko'chirish: {branch?.name} → …</h2>
      {error && <ErrorBox message={error} />}
      <div className="grid-2">
        <Field label="Qayerga">
          <select className="input" value={to} onChange={(e) => setTo(Number(e.target.value) || "")}>
            <option value="">Filialni tanlang</option>
            {targets.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </Field>
        <Field label="Izoh"><input className="input" value={note} onChange={(e) => setNote(e.target.value)} /></Field>
      </div>
      <VariantPicker branchId={branch?.id} onPick={(v) => {
        if (!lines.some((l) => l.variant === v.id)) {
          setLines([...lines, { variant: v.id, sku: v.sku, variant_name: `${v.product_name} / ${v.color_name} / ${v.size_name}`,
                                quantity: 1, available: v.stock ?? 0 }]);
        }
      }} />
      {lines.length > 0 && (
        <table className="table">
          <thead><tr><th>Variant</th><th className="right">Mavjud</th><th>Miqdor</th><th /></tr></thead>
          <tbody>
            {lines.map((l) => (
              <tr key={l.variant}>
                <td>{l.variant_name}<div className="muted">{l.sku}</div></td>
                <td className="right num">{l.available}</td>
                <td style={{ width: 100 }}>
                  <input className={`input ${l.quantity > l.available ? "invalid" : ""}`} inputMode="numeric" value={l.quantity}
                         onChange={(e) => setLines(lines.map((x) => x.variant === l.variant
                           ? { ...x, quantity: Math.max(1, Number(e.target.value.replace(/\D/g, "")) || 1) } : x))} />
                </td>
                <td><button className="btn btn-secondary btn-sm" aria-label="O'chirish"
                            onClick={() => setLines(lines.filter((x) => x.variant !== l.variant))}>✕</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-secondary" disabled={busy || !lines.length} onClick={() => save(false)}>Qoralama saqlash</button>
        <button className="btn btn-primary" disabled={busy || !lines.length} onClick={() => save(true)}>Saqlash va jo'natish</button>
      </div>
      <p className="muted" style={{ margin: 0 }}>Jo'natilganda tovar bu filial qoldig'idan ayriladi, qabul qilinganda ikkinchi filialga qo'shiladi.</p>
    </div>
  );
}

export function TransfersPage() {
  const { branch, isManager } = useAuth();
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const list = useAsync(() => api<Page<Transfer>>(`/inventory/transfers/${qs({ page })}`), [page, branch?.id]);

  async function act(t: Transfer, action: "send" | "receive" | "cancel", done: string) {
    setActionError(null);
    try {
      await api(`/inventory/transfers/${t.id}/${action}/`, { method: "POST" });
      setMessage(done);
      list.reload();
    } catch (e) {
      setActionError((e as Error).message);
    }
  }

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Ko'chirish</h1>
        {isManager && !creating && <button className="btn btn-primary" onClick={() => { setCreating(true); setMessage(null); }}>+ Yangi ko'chirish</button>}
      </div>
      {message && <Success>{message}</Success>}
      {actionError && <ErrorBox message={actionError} />}
      {creating && <NewTransfer onSaved={(t) => {
        setCreating(false);
        setMessage(t.status === "sent" ? "Tovar jo'natildi." : "Ko'chirish qoralama sifatida saqlandi.");
        list.reload();
      }} />}
      <div className="card" style={{ padding: 0 }}>
        {list.loading ? <Loading /> : list.error ? <div style={{ padding: 16 }}><ErrorBox message={list.error} onRetry={list.reload} /></div> :
          !list.data?.results.length ? <Empty title="Hali ko'chirish yo'q" hint="Filiallar orasida tovar ko'chirishni shu yerda boshlang." /> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>№</th><th>Sana</th><th>Qayerdan → Qayerga</th><th>Tovarlar</th><th>Holat</th><th /></tr></thead>
                <tbody>
                  {list.data.results.map((t) => (
                    <tr key={t.id}>
                      <td>{t.id}</td>
                      <td>{dateTime(t.created_at)}</td>
                      <td>{t.from_branch_name} → {t.to_branch_name}{t.note && <div className="muted">{t.note}</div>}</td>
                      <td>{t.lines.map((l) => <div key={l.variant} className="muted">{l.sku} × {l.quantity}</div>)}</td>
                      <td><DocStatusBadge status={t.status} /></td>
                      <td>
                        {isManager && (
                          <div className="row" style={{ gap: 6 }}>
                            {t.status === "draft" && <button className="btn btn-primary btn-sm" onClick={() => act(t, "send", "Tovar jo'natildi.")}>Jo'natish</button>}
                            {t.status === "sent" && <button className="btn btn-primary btn-sm" onClick={() => act(t, "receive", "Tovar qabul qilindi.")}>Qabul qilish</button>}
                            {(t.status === "draft" || t.status === "sent") && (
                              <button className="btn btn-danger btn-sm" onClick={() => act(t, "cancel", t.status === "sent" ? "Bekor qilindi, tovar jo'natgan filialga qaytdi." : "Bekor qilindi.")}>Bekor qilish</button>
                            )}
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
