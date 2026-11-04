import { useState, type FormEvent } from "react";

import { api, ApiError, qs } from "../api/client";
import type {
  NamedRef, Page, PricingSettings, Product, Promotion, PromotionKind, PromotionScope, PromotionStatus,
} from "../api/types";
import { Empty, ErrorBox, Field, Loading, Success } from "../components/ui";
import { money } from "../utils/format";
import { useAsync, useDebounced } from "../utils/useAsync";

interface Season extends NamedRef { start_month: number; end_month: number }

const SCOPES: { value: PromotionScope; label: string }[] = [
  { value: "all", label: "Barcha tovarlar" },
  { value: "season", label: "Mavsum bo'yicha" },
  { value: "category", label: "Kategoriya bo'yicha" },
  { value: "products", label: "Tanlangan tovarlar" },
];

const FILTERS: { value: PromotionStatus | ""; label: string }[] = [
  { value: "active", label: "Faol" },
  { value: "scheduled", label: "Boshlanmagan" },
  { value: "ended", label: "Tugagan" },
  { value: "stopped", label: "To'xtatilgan" },
  { value: "", label: "Hammasi" },
];

const STATUS_BADGE: Record<PromotionStatus, string> = {
  active: "badge-ok", scheduled: "badge-warn", ended: "badge-neutral", stopped: "badge-danger",
};

const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];

/** "2026-11-04" -> "04.11.2026" */
function day(iso: string) {
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

function todayIso() {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Tashkent" });
}

function addDays(iso: string, n: number) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** Mavsum oxirgi oyining oxirgi kuni (bugundan keyingi eng yaqin). */
function seasonEnd(season: Season, from: string) {
  const [y, m] = from.split("-").map(Number);
  let year = y;
  // Mavsum allaqachon tugagan bo'lsa (masalan, hozir mart, qish fevralda tugagan), keyingi yilnikini olamiz.
  const inSeason = season.start_month <= season.end_month
    ? m >= season.start_month && m <= season.end_month
    : m >= season.start_month || m <= season.end_month;
  if (!inSeason && m > season.end_month) year += 1;
  if (inSeason && season.start_month > season.end_month && m >= season.start_month) year += 1;
  const last = new Date(Date.UTC(year, season.end_month, 0)).getUTCDate();
  return `${year}-${String(season.end_month).padStart(2, "0")}-${String(last).padStart(2, "0")}`;
}

function scopeText(p: Promotion) {
  if (p.scope === "season") return `Mavsum: ${p.season_name}`;
  if (p.scope === "category") return `Kategoriya: ${p.category_name}`;
  if (p.scope === "products") {
    const names = p.product_names;
    return names.length <= 2 ? names.join(", ") : `${names.slice(0, 2).join(", ")} va yana ${names.length - 2} ta`;
  }
  return "Barcha tovarlar";
}

interface FormState {
  name: string; kind: PromotionKind; value: string; scope: PromotionScope;
  category: string; season: string; products: { id: number; name: string }[];
  starts_on: string; ends_on: string;
}

function initialForm(p: Promotion | null): FormState {
  if (!p) {
    const t = todayIso();
    return { name: "", kind: "percent", value: "", scope: "all", category: "", season: "", products: [],
             starts_on: t, ends_on: addDays(t, 13) };
  }
  return {
    name: p.name, kind: p.kind, value: String(Number(p.value)), scope: p.scope,
    category: p.category ? String(p.category) : "", season: p.season ? String(p.season) : "",
    products: p.products.map((id, i) => ({ id, name: p.product_names[i] ?? `#${id}` })),
    starts_on: p.starts_on, ends_on: p.ends_on,
  };
}

function ProductPicker({ value, onChange, error }: {
  value: { id: number; name: string }[]; onChange: (v: { id: number; name: string }[]) => void; error?: string;
}) {
  const [query, setQuery] = useState("");
  const search = useDebounced(query.trim(), 250);
  const results = useAsync(
    () => search ? api<Page<Product>>(`/catalog/products/${qs({ search, page_size: 8, is_active: true })}`) : Promise.resolve(null),
    [search],
  );
  const chosen = new Set(value.map((p) => p.id));
  return (
    <Field label="Tovarlar *" error={error}>
      <div className="row" style={{ gap: 6 }}>
        {value.map((p) => (
          <span key={p.id} className="badge badge-ok">
            {p.name}
            <button type="button" aria-label={`${p.name} ni olib tashlash`} onClick={() => onChange(value.filter((x) => x.id !== p.id))}
                    style={{ border: "none", background: "none", cursor: "pointer", color: "inherit", padding: 0 }}>✕</button>
          </span>
        ))}
      </div>
      <input className="input" type="search" placeholder="Tovar nomi yoki artikul" value={query}
             onChange={(e) => setQuery(e.target.value)} />
      {search && results.data && (
        <div className="stack" style={{ gap: 4 }}>
          {results.data.results.length === 0 && <span className="muted">Topilmadi</span>}
          {results.data.results.filter((p) => !chosen.has(p.id)).map((p) => (
            <button type="button" key={p.id} className="result-item" style={{ padding: "6px 10px" }}
                    onClick={() => { onChange([...value, { id: p.id, name: p.name }]); setQuery(""); }}>
              <span>{p.name} <span className="muted">· {p.article}</span></span>
              <span className="muted">+ Qo'shish</span>
            </button>
          ))}
        </div>
      )}
    </Field>
  );
}

function PromotionForm({ promo, onSaved, onCancel }: { promo: Promotion | null; onSaved: (msg: string) => void; onCancel: () => void }) {
  const [form, setForm] = useState<FormState>(() => initialForm(promo));
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const refs = useAsync(async () => {
    const [categories, seasons] = await Promise.all([
      api<Page<NamedRef>>("/catalog/categories/?page_size=200"),
      api<Page<Season>>("/catalog/seasons/?page_size=100"),
    ]);
    return { categories: categories.results, seasons: seasons.results };
  }, []);

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setForm((f) => ({ ...f, [k]: v }));

  function pickSeason(id: string) {
    const s = refs.data?.seasons.find((x) => String(x.id) === id);
    setForm((f) => ({
      ...f, season: id,
      // Mavsumiy aksiya odatda mavsum oxirigacha davom etadi.
      ends_on: s ? seasonEnd(s, f.starts_on || todayIso()) : f.ends_on,
      name: f.name || (s ? `${s.name} mavsumi chegirmasi` : f.name),
    }));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setFields({});
    try {
      await api(promo ? `/pricing/promotions/${promo.id}/` : "/pricing/promotions/", {
        method: promo ? "PATCH" : "POST",
        body: {
          name: form.name, kind: form.kind, value: form.value, scope: form.scope,
          category: form.category ? Number(form.category) : null,
          season: form.season ? Number(form.season) : null,
          products: form.products.map((p) => p.id),
          starts_on: form.starts_on, ends_on: form.ends_on,
        },
      });
      onSaved(promo ? "Aksiya saqlandi." : "Aksiya yaratildi. Muddat ichida kassada avtomatik qo'llanadi.");
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  const season = refs.data?.seasons.find((s) => String(s.id) === form.season);

  return (
    <form className="card stack" onSubmit={submit}>
      <h2 style={{ margin: 0 }}>{promo ? `Tahrirlash: ${promo.name}` : "Yangi aksiya"}</h2>
      {error && <ErrorBox message={error} />}
      {refs.error && <ErrorBox message={refs.error} onRetry={refs.reload} />}
      <div className="grid-2">
        <Field label="Nomi *" error={fields.name}>
          <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} required
                 placeholder="Masalan: Kuzgi chegirma" />
        </Field>
        <Field label="Qamrov *" error={fields.scope}>
          <select className="input" value={form.scope} onChange={(e) => set("scope", e.target.value as PromotionScope)}>
            {SCOPES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </Field>
        <Field label="Chegirma turi" error={fields.kind}>
          <select className="input" value={form.kind} onChange={(e) => set("kind", e.target.value as PromotionKind)}>
            <option value="percent">Foiz (%)</option>
            <option value="amount">Summa (har bir dona uchun, so'm)</option>
          </select>
        </Field>
        <Field label={form.kind === "percent" ? "Foiz *" : "Summa, so'm *"} error={fields.value}
               hint={form.kind === "percent" ? "1 dan 90 gacha" : undefined}>
          <input className="input" inputMode="numeric" value={form.value} required
                 onChange={(e) => set("value", e.target.value.replace(/[^\d]/g, ""))} />
        </Field>
        {form.scope === "season" && (
          <Field label="Mavsum *" error={fields.season}
                 hint={season ? `${MONTHS[season.start_month - 1]} – ${MONTHS[season.end_month - 1]}. Tugash sanasi mavsum oxiriga qo'yildi.` : undefined}>
            <select className="input" value={form.season} onChange={(e) => pickSeason(e.target.value)}>
              <option value="">Tanlang</option>
              {refs.data?.seasons.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
        )}
        {form.scope === "category" && (
          <Field label="Kategoriya *" error={fields.category}>
            <select className="input" value={form.category} onChange={(e) => set("category", e.target.value)}>
              <option value="">Tanlang</option>
              {refs.data?.categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
        )}
        <Field label="Boshlanish sanasi *" error={fields.starts_on}>
          <input className="input" type="date" value={form.starts_on} onChange={(e) => set("starts_on", e.target.value)} required />
        </Field>
        <Field label="Tugash sanasi *" error={fields.ends_on} hint="Shu kun ham kiradi">
          <input className="input" type="date" value={form.ends_on} onChange={(e) => set("ends_on", e.target.value)} required />
        </Field>
      </div>
      {form.scope === "products" && (
        <ProductPicker value={form.products} onChange={(v) => set("products", v)} error={fields.products} />
      )}
      <p className="muted" style={{ margin: 0 }}>
        Bir tovarga bir nechta aksiya to'g'ri kelsa, mijoz uchun eng foydalisi qo'llanadi. Aksiya narxni hech qachon
        tannarxdan pastga tushirmaydi.
      </p>
      <div className="row">
        <button type="button" className="btn btn-secondary" onClick={onCancel}>Bekor qilish</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saqlanmoqda..." : "Saqlash"}</button>
      </div>
    </form>
  );
}

function SettingsCard() {
  const settings = useAsync(() => api<PricingSettings>("/pricing/settings/"), []);
  const [value, setValue] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!settings.data) return null;
  const current = value ?? String(settings.data.cashier_max_discount_percent);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    setError(null);
    try {
      settings.setData(await api<PricingSettings>("/pricing/settings/", {
        method: "PATCH", body: { cashier_max_discount_percent: Number(current || 0) },
      }));
      setValue(null);
      setMsg("Saqlandi.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card stack" onSubmit={save}>
      <h2 style={{ margin: 0 }}>Chegirma sozlamalari</h2>
      {msg && <Success>{msg}</Success>}
      {error && <ErrorBox message={error} />}
      <div className="row" style={{ alignItems: "flex-end" }}>
        <div style={{ flex: "1 1 260px" }}>
          <Field label="Sotuvchi qo'lda beradigan chegirma chegarasi, %"
                 hint="Undan katta chegirmani faqat egasi yoki menejer bera oladi. 0 — sotuvchi qo'lda chegirma bera olmaydi.">
            <input className="input" inputMode="numeric" value={current}
                   onChange={(e) => setValue(e.target.value.replace(/[^\d]/g, "").slice(0, 3))} />
          </Field>
        </div>
        <button className="btn btn-primary" disabled={busy || value === null}>Saqlash</button>
      </div>
    </form>
  );
}

export function PromotionsPage() {
  const [status, setStatus] = useState<PromotionStatus | "">("active");
  const [editing, setEditing] = useState<Promotion | "new" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const list = useAsync(
    () => api<Page<Promotion>>(`/pricing/promotions/${qs({ status, page_size: 100 })}`).then((p) => p.results),
    [status],
  );

  async function act(p: Promotion, kind: "stop" | "resume" | "delete") {
    if (kind === "delete" && !window.confirm(`"${p.name}" aksiyasini o'chirasizmi?`)) return;
    if (kind === "stop" && !window.confirm(`"${p.name}" aksiyasini to'xtatasizmi? Kassada boshqa qo'llanmaydi.`)) return;
    setActionError(null);
    setMessage(null);
    try {
      if (kind === "delete") await api(`/pricing/promotions/${p.id}/`, { method: "DELETE" });
      else await api(`/pricing/promotions/${p.id}/${kind}/`, { method: "POST" });
      setMessage(kind === "delete" ? "Aksiya o'chirildi." : kind === "stop" ? "Aksiya to'xtatildi." : "Aksiya qayta yoqildi.");
      list.reload();
    } catch (err) {
      setActionError((err as Error).message);
    }
  }

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Aksiyalar</h1>
        {!editing && <button className="btn btn-primary" onClick={() => { setEditing("new"); setMessage(null); }}>+ Yangi aksiya</button>}
      </div>
      {message && <Success>{message}</Success>}
      {actionError && <ErrorBox message={actionError} />}
      {editing && (
        <PromotionForm key={editing === "new" ? "new" : editing.id} promo={editing === "new" ? null : editing}
                       onCancel={() => setEditing(null)}
                       onSaved={(msg) => { setEditing(null); setMessage(msg); list.reload(); }} />
      )}

      <div className="row" role="radiogroup" aria-label="Holat">
        {FILTERS.map((f) => (
          <button key={f.value} role="radio" aria-checked={status === f.value}
                  className={`chip ${status === f.value ? "on" : ""}`} onClick={() => setStatus(f.value)}>
            {f.label}
          </button>
        ))}
      </div>

      {list.loading && !list.data ? <Loading /> : list.error || !list.data ? (
        <ErrorBox message={list.error ?? "Xatolik"} onRetry={list.reload} />
      ) : list.data.length === 0 ? (
        <Empty title="Aksiya yo'q" hint="Yangi aksiya yarating: mavsum, kategoriya yoki tanlangan tovarlarga." />
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Aksiya</th><th>Qamrov</th><th>Muddat</th><th>Holat</th><th className="right">Natija</th><th /></tr>
              </thead>
              <tbody>
                {list.data.map((p) => (
                  <tr key={p.id}>
                    <td><b>{p.label}</b></td>
                    <td>{scopeText(p)}</td>
                    <td className="num" style={{ whiteSpace: "nowrap" }}>{day(p.starts_on)} – {day(p.ends_on)}</td>
                    <td><span className={`badge ${STATUS_BADGE[p.status]}`}>{p.status_display}</span></td>
                    <td className="right num">
                      {p.sales_count > 0 ? (
                        <>
                          <div>{p.units_sold} dona · {p.sales_count} savdo</div>
                          <div className="muted">Chegirma: {money(p.discount_given)}</div>
                        </>
                      ) : <span className="muted">Hali sotilmagan</span>}
                    </td>
                    <td>
                      <div className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => { setEditing(p); setMessage(null); }}>✎</button>
                        {p.is_active
                          ? p.status !== "ended" && <button className="btn btn-secondary btn-sm" onClick={() => act(p, "stop")}>To'xtatish</button>
                          : <button className="btn btn-secondary btn-sm" onClick={() => act(p, "resume")}>Yoqish</button>}
                        {p.sales_count === 0 && (
                          <button className="btn btn-danger btn-sm" aria-label="O'chirish" onClick={() => act(p, "delete")}>🗑</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <SettingsCard />
    </div>
  );
}
