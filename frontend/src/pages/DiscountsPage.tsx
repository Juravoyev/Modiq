import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, ApiError, qs } from "../api/client";
import type { Discount, DiscountKind, DiscountResults, DiscountState, Page, Variant } from "../api/types";
import { VariantPicker } from "../components/VariantPicker";
import { Empty, ErrorBox, Field, Loading, Pagination, Success } from "../components/ui";
import { isoDate, money } from "../utils/format";
import { useAsync } from "../utils/useAsync";

const STATES: { value: DiscountState | ""; label: string }[] = [
  { value: "", label: "Hammasi" },
  { value: "active", label: "Amalda" },
  { value: "scheduled", label: "Rejalashtirilgan" },
  { value: "draft", label: "Qoralama" },
  { value: "finished", label: "Tugagan" },
  { value: "cancelled", label: "Bekor qilingan" },
];

const STATE_BADGE: Record<DiscountState, string> = {
  draft: "badge-neutral", scheduled: "badge-warn", active: "badge-ok", finished: "badge-neutral", cancelled: "badge-danger",
};

function StateBadge({ state }: { state: DiscountState }) {
  return <span className={`badge ${STATE_BADGE[state]}`}>{STATES.find((s) => s.value === state)?.label}</span>;
}

/** Ko'rsatish uchun oldindan hisob. Saqlanadigan narxni server o'zi hisoblaydi. */
function previewPrice(before: number, kind: DiscountKind, value: number): number | null {
  if (!value || value <= 0) return null;
  if (kind === "percent") return value < 100 ? Math.round(before * (100 - value)) / 100 : null;
  return value < before ? value : null;
}

function NewDiscount({ initial, onSaved, onClose }: {
  initial: Variant | null; onSaved: (d: Discount) => void; onClose: () => void;
}) {
  const [variant, setVariant] = useState<Variant | null>(initial);
  const [kind, setKind] = useState<DiscountKind>("percent");
  const [value, setValue] = useState("");
  const [startsOn, setStartsOn] = useState(isoDate());
  const [endsOn, setEndsOn] = useState(isoDate(13));
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (initial) setVariant(initial); }, [initial]);

  const before = Number(variant?.effective_sale_price ?? 0);
  const cost = Number(variant?.effective_purchase_price ?? 0);
  const after = variant ? previewPrice(before, kind, Number(value)) : null;

  async function save() {
    if (!variant) return setError("Tovar variantini tanlang.");
    setBusy(true);
    setError(null);
    try {
      const d = await api<Discount>("/discounts/", {
        method: "POST",
        body: { variant: variant.id, kind, value, starts_on: startsOn, ends_on: endsOn, note },
      });
      onSaved(d);
    } catch (e) {
      const err = e as ApiError;
      setError([err.message, ...Object.values(err.fields ?? {})].join(" "));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card stack">
      <div className="spread">
        <h2 style={{ margin: 0 }}>Yangi chegirma</h2>
        <button className="btn btn-secondary btn-sm" onClick={onClose}>Yopish</button>
      </div>
      {error && <ErrorBox message={error} />}
      {variant ? (
        <div className="spread">
          <div>
            <b>{variant.product_name}</b> · {variant.color_name} / {variant.size_name}
            <div className="muted">{variant.sku} · qoldiq {variant.stock ?? 0} dona</div>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => setVariant(null)}>Boshqa tovar</button>
        </div>
      ) : (
        <VariantPicker onPick={setVariant} label="Qaysi tovarga" />
      )}
      <div className="grid-2">
        <Field label="Chegirma turi">
          <select className="input" value={kind} onChange={(e) => setKind(e.target.value as DiscountKind)}>
            <option value="percent">Foiz (%)</option>
            <option value="fixed_price">Yangi narx (so'm)</option>
          </select>
        </Field>
        <Field label={kind === "percent" ? "Foiz" : "Yangi narx"}>
          <input className="input" inputMode="decimal" value={value} placeholder={kind === "percent" ? "masalan, 20" : "masalan, 150000"}
                 onChange={(e) => setValue(e.target.value.replace(/[^\d.]/g, ""))} />
        </Field>
        <Field label="Boshlanish sanasi">
          <input className="input" type="date" value={startsOn} onChange={(e) => setStartsOn(e.target.value)} />
        </Field>
        <Field label="Tugash sanasi">
          <input className="input" type="date" value={endsOn} onChange={(e) => setEndsOn(e.target.value)} />
        </Field>
      </div>
      <Field label="Izoh (ixtiyoriy)">
        <input className="input" value={note} placeholder="masalan, mavsum oxiri" onChange={(e) => setNote(e.target.value)} />
      </Field>
      {variant && (
        <div className="facts">
          <span>Hozirgi narx: <b>{money(before)}</b></span>
          <span>Chegirmadan keyin: <b>{after !== null ? money(after) : "—"}</b></span>
          <span>Xarid narxi: <b>{money(cost)}</b></span>
          {after !== null && <span>1 dona uchun taxminiy yalpi foyda: <b>{money(after - cost)}</b></span>}
        </div>
      )}
      {after !== null && after < cost && (
        <div className="alert alert-warn">
          Yangi narx xarid narxidan past. Bunday chegirmani faqat menejer yoki egasi alohida tasdiq bilan qo'llashi mumkin.
        </div>
      )}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-primary" disabled={busy || !variant || !value} onClick={save}>Qoralama saqlash</button>
      </div>
      <p className="muted" style={{ margin: 0 }}>
        Chegirma tasdiqlangandan keyin kassada boshlanish sanasidan tugash sanasigacha avtomatik qo'llanadi.
      </p>
    </div>
  );
}

function Results({ id }: { id: number }) {
  const r = useAsync(() => api<DiscountResults>(`/reports/discounts/${id}/results/`), [id]);
  if (r.loading) return <Loading />;
  if (r.error) return <ErrorBox message={r.error} onRetry={r.reload} />;
  if (!r.data) return null;
  if (!r.data.started) return <p className="muted" style={{ margin: 0 }}>Chegirma hali boshlanmagan, natija yo'q.</p>;
  const { before, during, days, note } = r.data;
  return (
    <div className="stack" style={{ gap: 6 }}>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Davr</th><th className="right">Sotildi, dona</th><th className="right">Kuniga</th>
              <th className="right">Tushum</th><th className="right">Taxminiy yalpi foyda</th></tr>
          </thead>
          <tbody>
            {[["Chegirmadan oldin", before], ["Chegirma davrida", during]].map(([label, p]) => {
              const x = p as typeof before;
              return (
                <tr key={label as string}>
                  <td>{label as string}<div className="muted">{x.from} — {x.to}</div></td>
                  <td className="right num">{x.quantity}</td>
                  <td className="right num">{String(x.per_day).replace(".", ",")}</td>
                  <td className="right num">{money(x.revenue)}</td>
                  <td className="right num">{money(x.gross_profit)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="muted" style={{ margin: 0 }}>Har ikki davr {days} kundan. {note}</p>
    </div>
  );
}

function DiscountRow({ d, onChanged }: { d: Discount; onChanged: (msg: string) => void }) {
  const [open, setOpen] = useState(false);
  const [confirmBelow, setConfirmBelow] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act(action: "approve" | "cancel", msg: string) {
    setError(null);
    try {
      await api(`/discounts/${d.id}/${action}/`, {
        method: "POST", body: action === "approve" ? { allow_below_cost: confirmBelow } : undefined,
      });
      onChanged(msg);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const canCancel = d.status === "draft" || (d.status === "approved" && d.state !== "finished");
  return (
    <div className="card stack" style={{ gap: 8 }}>
      <div className="spread">
        <div>
          <b>{d.variant_name}</b>
          <div className="muted">{d.sku} · {d.starts_on} — {d.ends_on}{d.note && ` · ${d.note}`}</div>
        </div>
        <StateBadge state={d.state} />
      </div>
      <div className="facts">
        <span>Turi: <b>{d.kind === "percent" ? `${Number(d.value)}%` : "yangi narx"}</b></span>
        <span>Narx: <b><s className="muted">{money(d.price_before)}</s> → {money(d.price_after)}</b></span>
        <span>Xarid narxi: <b>{money(d.unit_cost)}</b></span>
        {d.below_cost && <span className="badge badge-danger">Xarid narxidan past</span>}
      </div>
      <div className="muted">
        Yaratdi: {d.created_by_name ?? "—"}{d.approved_by_name && ` · Tasdiqladi: ${d.approved_by_name}`}
      </div>
      {error && <ErrorBox message={error} />}
      {d.status === "draft" && d.below_cost && (
        <label className="alert alert-warn" style={{ cursor: "pointer" }}>
          <input type="checkbox" checked={confirmBelow} onChange={(e) => setConfirmBelow(e.target.checked)} />
          Narx xarid narxidan past ekanini bilaman va tasdiqlayman.
        </label>
      )}
      <div className="row" style={{ gap: 6 }}>
        {d.status === "draft" && (
          <button className="btn btn-primary btn-sm" disabled={d.below_cost && !confirmBelow}
                  onClick={() => act("approve", "Chegirma tasdiqlandi.")}>Tasdiqlash</button>
        )}
        {canCancel && <button className="btn btn-danger btn-sm" onClick={() => act("cancel", "Chegirma bekor qilindi.")}>Bekor qilish</button>}
        {(d.state === "active" || d.state === "finished") && (
          <button className="btn btn-secondary btn-sm" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? "Natijani yopish" : "Natijani ko'rish"}
          </button>
        )}
      </div>
      {open && <Results id={d.id} />}
    </div>
  );
}

export function DiscountsPage() {
  const [params, setParams] = useSearchParams();
  const variantId = Number(params.get("variant")) || null;
  const [state, setState] = useState<DiscountState | "">("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(Boolean(variantId));
  const [message, setMessage] = useState<string | null>(null);
  const list = useAsync(() => api<Page<Discount>>(`/discounts/${qs({ state, page })}`), [state, page]);
  const prefill = useAsync(
    () => (variantId ? api<Variant>(`/catalog/variants/${variantId}/`) : Promise.resolve(null)), [variantId],
  );

  function closeForm() {
    setCreating(false);
    if (variantId) setParams({});
  }

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Chegirmalar</h1>
        {!creating && <button className="btn btn-primary" onClick={() => { setCreating(true); setMessage(null); }}>+ Yangi chegirma</button>}
      </div>
      {message && <Success>{message}</Success>}
      {creating && (
        <NewDiscount initial={prefill.data} onClose={closeForm} onSaved={() => {
          closeForm();
          setMessage("Chegirma qoralama sifatida saqlandi. Kassada qo'llanishi uchun uni tasdiqlang.");
          setState("draft");
          setPage(1);
          list.reload();
        }} />
      )}
      <div className="row" style={{ gap: 8 }}>
        {STATES.map((s) => (
          <button key={s.value} className={`chip ${state === s.value ? "on" : ""}`} aria-pressed={state === s.value}
                  onClick={() => { setState(s.value); setPage(1); }}>{s.label}</button>
        ))}
      </div>
      {list.loading ? <Loading /> : list.error ? <ErrorBox message={list.error} onRetry={list.reload} /> :
        !list.data?.results.length ? (
          <Empty title="Chegirma yo'q" hint="Kam sotilayotgan tovarlar uchun chegirmani shu yerda yoki Aqlli tavsiyalar sahifasidan boshlang." />
        ) : (
          list.data.results.map((d) => (
            <DiscountRow key={d.id} d={d} onChanged={(msg) => { setMessage(msg); list.reload(); }} />
          ))
        )}
      {list.data && <Pagination page={page} count={list.data.count} onChange={setPage} />}
    </div>
  );
}
