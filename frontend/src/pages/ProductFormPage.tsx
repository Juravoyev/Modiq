import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { Color, NamedRef, Page, Product, Size } from "../api/types";
import { ErrorBox, Field, Loading } from "../components/ui";
import { useAsync } from "../utils/useAsync";

function Chips<T extends NamedRef>({ items, selected, onToggle }: { items: T[]; selected: number[]; onToggle: (id: number) => void }) {
  return (
    <div className="row" style={{ gap: 8 }}>
      {items.map((i) => (
        <button type="button" key={i.id} className={`chip ${selected.includes(i.id) ? "on" : ""}`}
                aria-pressed={selected.includes(i.id)} onClick={() => onToggle(i.id)}>
          {selected.includes(i.id) ? "✓ " : ""}{i.name}
        </button>
      ))}
    </div>
  );
}

function QuickAdd({ placeholder, onAdd }: { placeholder: string; onAdd: (name: string) => Promise<void> }) {
  const [value, setValue] = useState("");
  const [err, setErr] = useState<string | null>(null);
  async function add() {
    if (!value.trim()) return;
    try {
      await onAdd(value.trim());
      setValue("");
      setErr(null);
    } catch (e) {
      setErr((e as ApiError).fields?.name || (e as Error).message);
    }
  }
  return (
    <div className="stack" style={{ gap: 4 }}>
      <div className="row" style={{ gap: 8, flexWrap: "nowrap" }}>
        <input className="input" placeholder={placeholder} value={value} onChange={(e) => setValue(e.target.value)}
               onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void add(); } }} />
        <button type="button" className="btn btn-secondary" onClick={add}>Qo'shish</button>
      </div>
      {err && <span className="field-error">{err}</span>}
    </div>
  );
}

const toggle = (list: number[], id: number) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

export function ProductFormPage() {
  const navigate = useNavigate();
  const refs = useAsync(async () => {
    const [colors, sizes, categories, brands, seasons] = await Promise.all([
      api<Page<Color>>("/catalog/colors/?page_size=100"),
      api<Page<Size>>("/catalog/sizes/?page_size=100"),
      api<Page<NamedRef>>("/catalog/categories/"),
      api<Page<NamedRef>>("/catalog/brands/"),
      api<Page<NamedRef>>("/catalog/seasons/"),
    ]);
    return { colors: colors.results, sizes: sizes.results, categories: categories.results, brands: brands.results, seasons: seasons.results };
  }, []);

  const [form, setForm] = useState({ name: "", article: "", purchase_price: "", sale_price: "", min_stock: "1", category: "", brand: "", season: "" });
  const [colorIds, setColorIds] = useState<number[]>([]);
  const [sizeIds, setSizeIds] = useState<number[]>([]);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value });

  async function addRef(kind: "colors" | "sizes" | "categories", name: string) {
    const created = await api<NamedRef>(`/catalog/${kind}/`, { method: "POST", body: { name } });
    refs.setData((d) => (d ? { ...d, [kind]: [...d[kind], created] } : d));
    if (kind === "colors") setColorIds((s) => [...s, created.id]);
    if (kind === "sizes") setSizeIds((s) => [...s, created.id]);
    if (kind === "categories") setForm((f) => ({ ...f, category: String(created.id) }));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setFields({});
    try {
      await api<Product>("/catalog/products/", {
        method: "POST",
        body: {
          name: form.name, article: form.article, purchase_price: form.purchase_price, sale_price: form.sale_price,
          min_stock: Number(form.min_stock || 0),
          category: form.category ? Number(form.category) : null,
          brand: form.brand ? Number(form.brand) : null,
          season: form.season ? Number(form.season) : null,
          color_ids: colorIds, size_ids: sizeIds,
        },
      });
      navigate("/products");
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  if (refs.loading) return <Loading />;
  if (refs.error || !refs.data) return <ErrorBox message={refs.error ?? "Xatolik"} onRetry={refs.reload} />;
  const r = refs.data;
  const variantCount = colorIds.length * sizeIds.length;
  const belowCost = form.purchase_price && form.sale_price && Number(form.sale_price) < Number(form.purchase_price);

  return (
    <form className="stack" style={{ maxWidth: 760 }} onSubmit={submit}>
      <h1>Yangi tovar</h1>
      {error && <ErrorBox message={error} />}
      <div className="card stack">
        <div className="grid-2">
          <Field label="Tovar nomi *" error={fields.name}>
            <input className="input" value={form.name} onChange={set("name")} required placeholder="Futbolka Basic" />
          </Field>
          <Field label="Artikul *" error={fields.article} hint="SKU shu artikuldan yasaladi">
            <input className="input" value={form.article} onChange={set("article")} required placeholder="FB01" />
          </Field>
          <Field label="Xarid narxi (so'm) *" error={fields.purchase_price}>
            <input className="input" inputMode="decimal" value={form.purchase_price} onChange={set("purchase_price")} required />
          </Field>
          <Field label="Sotuv narxi (so'm) *" error={fields.sale_price}>
            <input className="input" inputMode="decimal" value={form.sale_price} onChange={set("sale_price")} required />
          </Field>
          <Field label="Minimal qoldiq (har bir variant)" error={fields.min_stock}>
            <input className="input" inputMode="numeric" value={form.min_stock} onChange={set("min_stock")} />
          </Field>
          <Field label="Kategoriya" error={fields.category}>
            <select className="input" value={form.category} onChange={set("category")}>
              <option value="">—</option>
              {r.categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Brend" error={fields.brand}>
            <select className="input" value={form.brand} onChange={set("brand")}>
              <option value="">—</option>
              {r.brands.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Mavsum" error={fields.season}>
            <select className="input" value={form.season} onChange={set("season")}>
              <option value="">—</option>
              {r.seasons.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
        </div>
        <QuickAdd placeholder="Yangi kategoriya" onAdd={(n) => addRef("categories", n)} />
        {belowCost && <div className="alert alert-warn"><span aria-hidden="true">▲</span> Sotuv narxi xarid narxidan past.</div>}
      </div>

      <div className="card stack">
        <h2 style={{ margin: 0 }}>Ranglar</h2>
        <Chips items={r.colors} selected={colorIds} onToggle={(id) => setColorIds(toggle(colorIds, id))} />
        <QuickAdd placeholder="Yangi rang, masalan: Qora" onAdd={(n) => addRef("colors", n)} />
        <h2 style={{ margin: "8px 0 0" }}>O'lchamlar</h2>
        <Chips items={r.sizes} selected={sizeIds} onToggle={(id) => setSizeIds(toggle(sizeIds, id))} />
        <QuickAdd placeholder="Yangi o'lcham, masalan: M yoki 42" onAdd={(n) => addRef("sizes", n)} />
        {fields.color_ids && <span className="field-error">{fields.color_ids}</span>}
        <p className="muted" style={{ margin: 0 }}>
          {variantCount > 0
            ? `${colorIds.length} rang × ${sizeIds.length} o'lcham = ${variantCount} ta variant (SKU) yaratiladi. Har birining qoldig'i alohida hisoblanadi.`
            : "Rang va o'lcham tanlang: har bir kombinatsiya alohida SKU bo'ladi."}
        </p>
      </div>

      <div className="row">
        <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>Bekor qilish</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saqlanmoqda..." : "Saqlash"}</button>
      </div>
    </form>
  );
}
