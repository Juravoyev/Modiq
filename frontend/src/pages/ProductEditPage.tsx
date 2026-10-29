import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, ApiError, qs } from "../api/client";
import type { Color, NamedRef, Page, Product, Size, Variant } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ImagePicker } from "../components/ImagePicker";
import { ErrorBox, Field, Loading, StockBadge, Success } from "../components/ui";
import { money } from "../utils/format";
import { useAsync } from "../utils/useAsync";
import { Chips, QuickAdd, toggle } from "./ProductFormPage";

interface Refs { colors: Color[]; sizes: Size[]; categories: NamedRef[]; brands: NamedRef[]; seasons: NamedRef[] }

const formOf = (p: Product) => ({
  name: p.name, article: p.article, purchase_price: p.purchase_price ?? "", sale_price: p.sale_price,
  min_stock: String(p.min_stock), category: p.category ? String(p.category) : "",
  brand: p.brand ? String(p.brand) : "", season: p.season ? String(p.season) : "",
});

/** Bitta variant qatori: SKU, shtrix-kod va alohida narxni tahrirlash, arxivlash. */
function VariantRow({ v, onSaved, onRemoved }: { v: Variant; onSaved: (v: Variant) => void; onRemoved: () => void }) {
  const [form, setForm] = useState({ sku: v.sku, barcode: v.barcode, sale_price: v.sale_price ?? "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = form.sku !== v.sku || form.barcode !== v.barcode || form.sale_price !== (v.sale_price ?? "");

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      const err = e as ApiError;
      setError(Object.values(err.fields ?? {})[0] || err.message);
    } finally {
      setBusy(false);
    }
  }

  const save = () => run(async () => {
    // Bo'sh narx = tovarning umumiy narxi ishlatiladi.
    onSaved({ ...v, ...await api<Variant>(`/catalog/variants/${v.id}/`, {
      method: "PATCH", body: { sku: form.sku, barcode: form.barcode, sale_price: form.sale_price || null },
    }), stock: v.stock });
  });
  const setActive = (is_active: boolean) => run(async () => {
    onSaved({ ...v, ...await api<Variant>(`/catalog/variants/${v.id}/`, { method: "PATCH", body: { is_active } }), stock: v.stock });
  });
  const remove = () => run(async () => {
    if (!window.confirm(`${v.sku} variantini o'chirasizmi? Tarixi bo'lsa, arxivlanadi.`)) return;
    const res = await api<{ archived?: boolean } | null>(`/catalog/variants/${v.id}/`, { method: "DELETE" });
    if (res?.archived) onSaved({ ...v, is_active: false });
    else onRemoved();
  });

  return (
    <tr style={v.is_active ? undefined : { opacity: 0.6 }}>
      <td>{v.color_name} · {v.size_name}</td>
      <td><input className="input" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} aria-label="SKU" /></td>
      <td><input className="input" value={form.barcode} placeholder="—" onChange={(e) => setForm({ ...form, barcode: e.target.value })} aria-label="Shtrix-kod" /></td>
      <td style={{ width: 140 }}>
        <input className="input" inputMode="decimal" value={form.sale_price} placeholder={money(v.effective_sale_price)}
               onChange={(e) => setForm({ ...form, sale_price: e.target.value.replace(/[^\d.]/g, "") })} aria-label="Alohida narx" />
      </td>
      <td className="right num">{v.stock ?? 0}<div><StockBadge quantity={v.stock ?? 0} min={v.effective_min_stock} /></div></td>
      <td>
        <div className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
          {dirty && <button className="btn btn-primary btn-sm" disabled={busy} onClick={save}>Saqlash</button>}
          {v.is_active
            ? <button className="btn btn-secondary btn-sm" disabled={busy} onClick={remove}>O'chirish</button>
            : <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => setActive(true)}>Faollashtirish</button>}
        </div>
        {error && <span className="field-error">{error}</span>}
      </td>
    </tr>
  );
}

export function ProductEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { branch } = useAuth();

  const loaded = useAsync(async () => {
    const [product, colors, sizes, categories, brands, seasons] = await Promise.all([
      api<Product>(`/catalog/products/${id}/${qs({ branch: branch?.id })}`),
      api<Page<Color>>("/catalog/colors/?page_size=100"),
      api<Page<Size>>("/catalog/sizes/?page_size=100"),
      api<Page<NamedRef>>("/catalog/categories/?page_size=100"),
      api<Page<NamedRef>>("/catalog/brands/?page_size=100"),
      api<Page<NamedRef>>("/catalog/seasons/?page_size=100"),
    ]);
    const refs: Refs = { colors: colors.results, sizes: sizes.results, categories: categories.results, brands: brands.results, seasons: seasons.results };
    return { product, refs };
  }, [id, branch?.id]);

  if (loaded.loading && !loaded.data) return <Loading />;
  if (loaded.error || !loaded.data) return <ErrorBox message={loaded.error ?? "Xatolik"} onRetry={loaded.reload} />;
  return (
    <ProductEditor key={loaded.data.product.id} initial={loaded.data.product} refs={loaded.data.refs}
                   onReload={loaded.reload} onDeleted={() => navigate("/products", { state: { notice: "Tovar o'chirildi." } })} />
  );
}

function ProductEditor({ initial, refs, onReload, onDeleted }: {
  initial: Product; refs: Refs; onReload: () => void; onDeleted: () => void;
}) {
  const [product, setProduct] = useState(initial);
  const [form, setForm] = useState(() => formOf(initial));
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [colorIds, setColorIds] = useState<number[]>([]);
  const [sizeIds, setSizeIds] = useState<number[]>([]);
  const [r, setRefs] = useState(refs);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value });

  async function act(fn: () => Promise<string | void>) {
    setBusy(true);
    setError(null);
    setMessage(null);
    setFields({});
    try {
      const msg = await fn();
      if (msg) setMessage(msg);
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  const save = (e: FormEvent) => {
    e.preventDefault();
    void act(async () => {
      const updated = await api<Product>(`/catalog/products/${product.id}/`, {
        method: "PATCH",
        body: {
          name: form.name, article: form.article, purchase_price: form.purchase_price, sale_price: form.sale_price,
          min_stock: Number(form.min_stock || 0),
          category: form.category ? Number(form.category) : null,
          brand: form.brand ? Number(form.brand) : null,
          season: form.season ? Number(form.season) : null,
        },
      });
      // Javobdagi qoldiq filial filtrisiz hisoblangan, shuning uchun variantlar o'zgarmaydi.
      setProduct({ ...updated, variants: product.variants, total_stock: product.total_stock });
      return "O'zgarishlar saqlandi.";
    });
  };

  const image = (method: "POST" | "DELETE", file?: File) => act(async () => {
    let body: FormData | undefined;
    if (file) {
      body = new FormData();
      body.append("image", file);
    }
    const updated = await api<Product>(`/catalog/products/${product.id}/image/`, { method, body });
    setProduct({ ...product, image: updated.image });
  });

  const generate = () => act(async () => {
    const res = await api<{ created: number }>(`/catalog/products/${product.id}/generate-variants/`, {
      method: "POST", body: { color_ids: colorIds, size_ids: sizeIds },
    });
    setColorIds([]);
    setSizeIds([]);
    onReload();
    return res.created ? `${res.created} ta yangi variant qo'shildi.` : "Bu kombinatsiyalar allaqachon mavjud.";
  });

  const setActive = (is_active: boolean) => act(async () => {
    await api(`/catalog/products/${product.id}/`, { method: "PATCH", body: { is_active } });
    setProduct({ ...product, is_active });
    return is_active ? "Tovar qayta faollashtirildi." : undefined;
  });

  const remove = () => act(async () => {
    if (!window.confirm(`"${product.name}" tovarini o'chirasizmi? Savdo yoki qoldiq tarixi bo'lsa, arxivlanadi.`)) return;
    const res = await api<{ archived?: boolean } | null>(`/catalog/products/${product.id}/`, { method: "DELETE" });
    if (!res?.archived) return onDeleted();
    setProduct({ ...product, is_active: false });
    return "Tovarning tarixi bor, shuning uchun o'chirilmadi, arxivlandi. Kassada endi ko'rinmaydi.";
  });

  async function addRef(kind: "colors" | "sizes", name: string) {
    const created = await api<Color & Size>(`/catalog/${kind}/`, { method: "POST", body: { name } });
    setRefs((d) => ({ ...d, [kind]: [...d[kind], created] }));
    if (kind === "colors") setColorIds((s) => [...s, created.id]);
    else setSizeIds((s) => [...s, created.id]);
  }

  const belowCost = form.purchase_price && form.sale_price && Number(form.sale_price) < Number(form.purchase_price);

  return (
    <div className="stack" style={{ maxWidth: 960 }}>
      <div className="spread">
        <div>
          <Link to="/products" className="muted">‹ Tovarlar</Link>
          <h1 style={{ margin: "4px 0 0" }}>
            {product.name}
            {!product.is_active && <span className="badge badge-neutral" style={{ marginLeft: 8, verticalAlign: "middle" }}>Arxivda</span>}
          </h1>
        </div>
        <div className="row">
          {product.is_active
            ? <button className="btn btn-danger" disabled={busy} onClick={remove}>O'chirish</button>
            : <button className="btn btn-primary" disabled={busy} onClick={() => setActive(true)}>Faollashtirish</button>}
        </div>
      </div>
      {message && <Success>{message}</Success>}
      {error && <ErrorBox message={error} />}

      <form className="card stack" onSubmit={save}>
        <h2 style={{ margin: 0 }}>Asosiy ma'lumotlar</h2>
        <div className="grid-2">
          <Field label="Tovar nomi *" error={fields.name}>
            <input className="input" value={form.name} onChange={set("name")} required />
          </Field>
          <Field label="Artikul *" error={fields.article} hint="O'zgartirilsa, mavjud SKUlar o'zgarmaydi">
            <input className="input" value={form.article} onChange={set("article")} required />
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
        {belowCost && <div className="alert alert-warn"><span aria-hidden="true">▲</span> Sotuv narxi xarid narxidan past.</div>}
        <div><button className="btn btn-primary" disabled={busy}>{busy ? "Saqlanmoqda..." : "Saqlash"}</button></div>
      </form>

      <div className="card stack">
        <h2 style={{ margin: 0 }}>Rasm</h2>
        <ImagePicker key={product.image ?? "none"} current={product.image} busy={busy}
                     onPick={(f) => void image("POST", f)} onRemove={() => void image("DELETE")} />
        <span className="muted">Rasm darhol saqlanadi va avtomatik siqiladi.</span>
      </div>

      <div className="card stack">
        <h2 style={{ margin: 0 }}>Variantlar</h2>
        {product.variants.length === 0 ? <span className="muted">Variantlar yo'q. Quyida rang va o'lcham tanlab qo'shing.</span> : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Rang · O'lcham</th><th>SKU</th><th>Shtrix-kod</th><th>Alohida narx</th><th className="right">Qoldiq</th><th /></tr></thead>
              <tbody>
                {product.variants.map((v) => (
                  <VariantRow key={v.id} v={v}
                              onSaved={(nv) => setProduct((p) => ({ ...p, variants: p.variants.map((x) => (x.id === nv.id ? nv : x)) }))}
                              onRemoved={() => setProduct((p) => ({ ...p, variants: p.variants.filter((x) => x.id !== v.id) }))} />
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="muted" style={{ margin: 0 }}>Alohida narx bo'sh bo'lsa, tovarning umumiy sotuv narxi ishlatiladi.</p>

        <h3 style={{ margin: "8px 0 0" }}>Yangi variantlar qo'shish</h3>
        <span className="field-label">Ranglar</span>
        <Chips items={r.colors} selected={colorIds} onToggle={(cid) => setColorIds(toggle(colorIds, cid))} />
        <QuickAdd placeholder="Yangi rang" onAdd={(n) => addRef("colors", n)} />
        <span className="field-label">O'lchamlar</span>
        <Chips items={r.sizes} selected={sizeIds} onToggle={(sid) => setSizeIds(toggle(sizeIds, sid))} />
        <QuickAdd placeholder="Yangi o'lcham" onAdd={(n) => addRef("sizes", n)} />
        <div>
          <button className="btn btn-primary" disabled={busy || !colorIds.length || !sizeIds.length} onClick={generate}>
            {colorIds.length && sizeIds.length ? `${colorIds.length * sizeIds.length} ta kombinatsiyani qo'shish` : "Rang va o'lcham tanlang"}
          </button>
        </div>
        <p className="muted" style={{ margin: 0 }}>Mavjud kombinatsiyalar takror yaratilmaydi.</p>
      </div>
    </div>
  );
}
