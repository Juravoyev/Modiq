import { Fragment, useState } from "react";

import { api, ApiError, qs } from "../api/client";
import type { Branch, Page, Transfer, TransferLine, TransferStatus, Variant } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorBox, Field, Loading, Pagination, Success } from "../components/ui";
import { dateTime } from "../utils/format";
import { useAsync, useDebounced } from "../utils/useAsync";

const STATUS: Record<TransferStatus, { label: string; cls: string; icon: string }> = {
  draft: { label: "Qoralama", cls: "badge-neutral", icon: "○" },
  sent: { label: "Yo'lda", cls: "badge-warn", icon: "➜" },
  received: { label: "Qabul qilingan", cls: "badge-ok", icon: "✓" },
  cancelled: { label: "Bekor qilingan", cls: "badge-danger", icon: "✕" },
};

type Line = TransferLine & { available: number };

function NewTransfer({ branches, onSaved }: { branches: Branch[]; onSaved: (t: Transfer) => void }) {
  const { branch } = useAuth();
  const targets = branches.filter((b) => b.is_active && b.id !== branch?.id);
  const [toBranch, setToBranch] = useState(targets[0]?.id ?? 0);
  const [note, setNote] = useState("");
  const [lines, setLines] = useState<Line[]>([]);
  const [query, setQuery] = useState("");
  const search = useDebounced(query.trim());
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const results = useAsync(
    () => (search ? api<Page<Variant>>(`/catalog/variants/${qs({ search, branch: branch?.id, is_active: true })}`) : Promise.resolve(null)),
    [search, branch?.id],
  );

  function add(v: Variant) {
    if (!lines.some((l) => l.variant === v.id)) {
      setLines([...lines, { variant: v.id, sku: v.sku, variant_name: `${v.product_name} / ${v.color_name} / ${v.size_name}`,
                            quantity: 1, available: v.stock ?? 0 }]);
    }
    setQuery("");
  }

  async function save(send: boolean) {
    if (!branch) return;
    setBusy(true);
    setError(null);
    setFields({});
    try {
      let t = await api<Transfer>("/inventory/transfers/", {
        method: "POST",
        body: { from_branch: branch.id, to_branch: toBranch, note, lines: lines.map(({ variant, quantity }) => ({ variant, quantity })) },
      });
      if (send) t = await api<Transfer>(`/inventory/transfers/${t.id}/send/`, { method: "POST" });
      onSaved(t);
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  if (!targets.length) {
    return <div className="alert alert-warn">Ko'chirish uchun kamida ikkita faol filial kerak. Avval "Filiallar" bo'limida yangi filial qo'shing.</div>;
  }
  const over = lines.filter((l) => l.quantity > l.available);

  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>Yangi ko'chirish · {branch?.name} dan</h2>
      {error && <ErrorBox message={error} />}
      <div className="grid-2">
        <Field label="Qayerga" error={fields.to_branch}>
          <select className="input" value={toBranch} onChange={(e) => setToBranch(Number(e.target.value))}>
            {targets.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </Field>
        <Field label="Izoh" error={fields.note}>
          <input className="input" value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
      </div>
      <Field label="Tovar qo'shish" error={fields.lines}>
        <input className="input" type="search" placeholder="SKU yoki tovar nomi" value={query} onChange={(e) => setQuery(e.target.value)} />
      </Field>
      {search && (results.loading ? <Loading text="Qidirilmoqda..." /> : (
        <div className="stack" style={{ gap: 6 }}>
          {results.data?.results.map((v) => (
            <button key={v.id} className="result-item" onClick={() => add(v)} disabled={(v.stock ?? 0) <= 0}>
              <span>{v.product_name} · {v.color_name} · {v.size_name}</span>
              <span className="muted">{v.sku} · {v.stock ?? 0} dona</span>
            </button>
          ))}
          {results.data && !results.data.results.length && <span className="muted">Topilmadi</span>}
        </div>
      ))}
      {lines.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Variant</th><th className="right">Mavjud</th><th>Miqdor</th><th /></tr></thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.variant}>
                  <td>{l.variant_name}<div className="muted">{l.sku}</div></td>
                  <td className="right num">{l.available}</td>
                  <td style={{ width: 110 }}>
                    <input className={`input ${l.quantity > l.available ? "invalid" : ""}`} inputMode="numeric" value={l.quantity}
                           onChange={(e) => setLines(lines.map((x) => (x.variant === l.variant
                             ? { ...x, quantity: Math.max(1, Number(e.target.value.replace(/\D/g, "")) || 1) } : x)))} />
                  </td>
                  <td><button className="btn btn-secondary btn-sm" aria-label="O'chirish"
                              onClick={() => setLines(lines.filter((x) => x.variant !== l.variant))}>✕</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {over.length > 0 && <span className="field-error">Miqdor qoldiqdan ko'p: {over.map((l) => l.sku).join(", ")}</span>}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-secondary" disabled={busy || !lines.length} onClick={() => save(false)}>Qoralama saqlash</button>
        <button className="btn btn-primary" disabled={busy || !lines.length || over.length > 0} onClick={() => save(true)}>Saqlash va jo'natish</button>
      </div>
      <p className="muted" style={{ margin: 0 }}>
        Jo'natilganda tovar bu filial qoldig'idan chiqadi, qabul qilinganda boshqa filialga qo'shiladi.
      </p>
    </div>
  );
}

export function TransfersPage() {
  const { branch, me } = useAuth();
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const branches = useAsync(() => api<Page<Branch>>("/auth/branches/?page_size=100").then((p) => p.results), []);
  const list = useAsync(() => api<Page<Transfer>>(`/inventory/transfers/${qs({ page })}`), [page]);
  const allowed = new Set((me?.branches ?? []).map((b) => b.id));

  async function run(t: Transfer, action: "send" | "receive" | "cancel", done: string) {
    if (action === "cancel" && !window.confirm(`№ ${t.id} ko'chirishni bekor qilasizmi?`)) return;
    setBusy(true);
    setActionError(null);
    setMessage(null);
    try {
      await api(`/inventory/transfers/${t.id}/${action}/`, { method: "POST" });
      setMessage(done);
      list.reload();
    } catch (e) {
      setActionError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Ko'chirish</h1>
        {!creating && <button className="btn btn-primary" onClick={() => { setCreating(true); setMessage(null); }}>+ Yangi ko'chirish</button>}
      </div>
      {message && <Success>{message}</Success>}
      {actionError && <ErrorBox message={actionError} />}
      {creating && (branches.loading ? <Loading /> : branches.error ? <ErrorBox message={branches.error} onRetry={branches.reload} /> : (
        <NewTransfer key={branch?.id} branches={branches.data ?? []} onSaved={(t) => {
          setCreating(false);
          setMessage(t.status === "sent" ? `Tovar "${t.to_branch_name}" filialiga jo'natildi.` : "Ko'chirish qoralama sifatida saqlandi.");
          list.reload();
        }} />
      ))}
      {creating && <div><button className="btn btn-secondary btn-sm" onClick={() => setCreating(false)}>Bekor qilish</button></div>}

      <div className="card" style={{ padding: 0 }}>
        {list.loading ? <Loading /> : list.error ? <div style={{ padding: 16 }}><ErrorBox message={list.error} onRetry={list.reload} /></div> :
          !list.data?.results.length ? <Empty title="Hali ko'chirish yo'q" hint="Tovarni ombordan do'konga yoki filiallar o'rtasida ko'chiring." /> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>№</th><th>Sana</th><th>Qayerdan → Qayerga</th><th className="right">Miqdor</th><th>Holat</th><th /></tr></thead>
                <tbody>
                  {list.data.results.map((t) => (
                    <Fragment key={t.id}>
                      <tr style={{ cursor: "pointer" }} onClick={() => setOpen(open === t.id ? null : t.id)}>
                        <td>{open === t.id ? "▾" : "▸"} {t.id}</td>
                        <td>{dateTime(t.created_at)}</td>
                        <td>{t.from_branch_name} → {t.to_branch_name}{t.note && <div className="muted">{t.note}</div>}</td>
                        <td className="right num">{t.lines.reduce((n, l) => n + l.quantity, 0)}</td>
                        <td><span className={`badge ${STATUS[t.status].cls}`}>{STATUS[t.status].icon} {STATUS[t.status].label}</span></td>
                        <td onClick={(e) => e.stopPropagation()}>
                          <div className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
                            {t.status === "draft" && allowed.has(t.from_branch) &&
                              <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => run(t, "send", "Tovar jo'natildi.")}>Jo'natish</button>}
                            {t.status === "sent" && allowed.has(t.to_branch) &&
                              <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => run(t, "receive", "Tovar qabul qilindi, qoldiq yangilandi.")}>Qabul qilish</button>}
                            {(t.status === "draft" || t.status === "sent") && allowed.has(t.from_branch) &&
                              <button className="btn btn-secondary btn-sm" disabled={busy}
                                      onClick={() => run(t, "cancel", t.status === "sent" ? "Bekor qilindi, tovar qaytarildi." : "Bekor qilindi.")}>Bekor qilish</button>}
                          </div>
                        </td>
                      </tr>
                      {open === t.id && (
                        <tr>
                          <td colSpan={6} style={{ background: "var(--bg)" }}>
                            {t.lines.map((l) => (
                              <div key={l.variant} className="spread" style={{ padding: "4px 0" }}>
                                <span>{l.variant_name} <span className="muted">{l.sku}</span></span>
                                <span className="num">{l.quantity} dona</span>
                              </div>
                            ))}
                            <div className="muted" style={{ marginTop: 6 }}>
                              {t.sent_at && <>Jo'natilgan: {dateTime(t.sent_at)}. </>}
                              {t.received_at && <>Qabul qilingan: {dateTime(t.received_at)}. </>}
                              {t.cancelled_at && <>Bekor qilingan: {dateTime(t.cancelled_at)}.</>}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
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
