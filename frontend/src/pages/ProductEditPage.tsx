import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { Color, NamedRef, Page, Product, Size, Variant } from "../api/types";
import { ErrorBox, Field, Loading, StockBadge, Success } from "../components/ui";
import { money } from "../utils/format";
import { useAsync } from "../utils/useAsync";

interface VariantEdit { barcode: string; sale_price: string; min_stock: string; is_active: boolean }

const toEdit = (v: Variant): VariantEdit => ({
  barcode: v.barcode, sale_price: v.sale_price ?? "", min_stock: v.min_stock === null ? "" : String(v.min_stock), is_active: v.is_active,
});

export function ProductEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const data = useAsync(async () => {
    const [product, colors, sizes, categories, brands, seasons] = await Promise.all([
      api<Product>(`/catalog/products/${id}/`),
      api<Page<Color>>("/catalog/colors/?page_size=200"),
      api<Page<Size>>("/catalog/sizes/?page_size=200"),
      api<Page<NamedRef>>("/catalog/categories/?page_size=200"),
      api<Page<NamedRef>>("/catalog/brands/?page_size=200"),
      api<Page<NamedRef>>("/catalog/seasons/?page_size=200"),
    ]);
    return { product, colors: colors.results, sizes: sizes.results, categories: categories.results, brands: brands.results, seasons: seasons.results };
  }, [id]);

  const [form, setForm] = useState<Record<string, string | boolean>>({});
  const [variants, setVariants] = useState<Record<number, VariantEdit>>({});
  const [newColors, setNewColors] = useState<number[]>([]);
  const [newSizes, setNewSizes] = useState<number[]>([]);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const p = data.data?.product;
    if (!p) return;
    setForm({
      name: p.name, article: p.article, purchase_price: p.purchase_price, sale_price: p.sale_price,
      min_stock: String(p.min_stock), category: p.category ? String(p.category) : "", brand: p.brand ? String(p.brand) : "",
      season: p.season ? String(p.season) : "", is_active: p.is_active,
    });
    setVariants(Object.fromEntries(p.variants.map((v) => [v.id, toEdit(v)])));
  }, [data.data]);

  if (data.loading) return <Loading />;
  if (data.error || !data.data) return <ErrorBox message={data.error ?? "Xatolik"} onRetry={data.reload} />;
  const { product, colors, sizes, categories, brands, seasons } = data.data;
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });
  const toggle = (list: number[], v: number) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  async function save() {
    setBusy(true);
    setError(null);
    setFields({});
    setSaved(null);
    try {
      await api(`/catalog/products/${id}/`, {
        method: "PATCH",
        body: {
          name: form.name, article: form.article, purchase_price: form.purchase_price, sale_price: form.sale_price,
          min_stock: Number(form.min_stock || 0), is_active: form.is_active,
          category: form.category ? Number(form.category) : null, brand: form.brand ? Number(form.brand) : null,
          season: form.season ? Number(form.season) : null,
        },
      });
      for (const v of product.variants) {
        const e = variants[v.id];
        const before = toEdit(v);
        if (JSON.stringify(e) === JSON.stringify(before)) continue;
        await api(`/catalog/variants/${v.id}/`, {
          method: "PATCH",
          body: { barcode: e.barcode, sale_price: e.sale_price || null, min_stock: e.min_stock === "" ? null : Number(e.min_stock), is_active: e.is_active },
        });
      }
      let msg = "O'zgarishlar saqlandi.";
      if (newColors.length && newSizes.length) {
        const r = await api<{ created: number }>(`/catalog/products/${id}/generate-variants/`, {
          method: "POST", body: { color_ids: newColors, size_ids: newSizes },
        });
        msg += ` ${r.created} ta yangi variant qo'shildi.`;
        setNewColors([]);
        setNewSizes([]);
      }
      setSaved(msg);
      data.reload();
    } catch (e) {
      setError((e as Error).message);
      if (e instanceof ApiError) setFields(e.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack" style={{ maxWidth: 900 }}>
      <div className="spread">
        <h1 style={{ margin: 0 }}>Tovarni tahrirlash</h1>
        <button className="btn btn-secondary" onClick={() => navigate("/products")}>‹ Tovarlar</button>
      </div>
      {error && <ErrorBox message={error} />}
      {saved && <Success>{saved}</Success>}
      <div className="card stack">
        <div className="grid-2">
          <Field label="Tovar nomi" error={fields.name}><input className="input" value={String(form.name ?? "")} onChange={set("name")} /></Field>
          <Field label="Artikul" error={fields.article} hint="O'zgartirilsa, mavjud SKU'lar o'zgarmaydi">
            <input className="input" value={String(form.article ?? "")} onChange={set("article")} />
          </Field>
          <Field label="Xarid narxi (so'm)" error={fields.purchase_price}><input className="input" inputMode="decimal" value={String(form.purchase_price ?? "")} onChange={set("purchase_price")} /></Field>
          <Field label="Sotuv narxi (so'm)" error={fields.sale_price}><input className="input" inputMode="decimal" value={String(form.sale_price ?? "")} onChange={set("sale_price")} /></Field>
          <Field label="Minimal qoldiq (har bir variant)" error={fields.min_stock}><input className="input" inputMode="numeric" value={String(form.min_stock ?? "")} onChange={set("min_stock")} /></Field>
          <Field label="Kategoriya"><select className="input" value={String(form.category ?? "")} onChange={set("category")}><option value="">—</option>{categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
          <Field label="Brend"><select className="input" value={String(form.brand ?? "")} onChange={set("brand")}><option value="">—</option>{brands.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
          <Field label="Mavsum"><select className="input" value={String(form.season ?? "")} onChange={set("season")}><option value="">—</option>{seasons.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
        </div>
        <label className="row" style={{ gap: 8 }}>
          <input type="checkbox" checked={Boolean(form.is_active)} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Faol (o'chirilsa kassada ko'rinmaydi, tarix saqlanadi)
        </label>
      </div>

      <div className="card stack">
        <h2 style={{ margin: 0 }}>Variantlar</h2>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>SKU</th><th>Rang / o'lcham</th><th className="right">Qoldiq</th><th>Shtrix-kod</th><th>Narx (bo'sh = tovar narxi)</th><th>Min.</th><th>Faol</th></tr></thead>
            <tbody>
              {product.variants.map((v) => {
                const e = variants[v.id];
                if (!e) return null;
                const upd = (patch: Partial<VariantEdit>) => setVariants({ ...variants, [v.id]: { ...e, ...patch } });
                return (
                  <tr key={v.id}>
                    <td>{v.sku}</td>
                    <td>{v.color_name} / {v.size_name}</td>
                    <td className="right num">{v.stock ?? 0} <StockBadge quantity={v.stock ?? 0} min={v.effective_min_stock} /></td>
                    <td style={{ minWidth: 130 }}><input className="input" value={e.barcode} onChange={(x) => upd({ barcode: x.target.value })} /></td>
                    <td style={{ minWidth: 130 }}><input className="input" inputMode="decimal" placeholder={money(product.sale_price)} value={e.sale_price} onChange={(x) => upd({ sale_price: x.target.value.replace(/[^\d.]/g, "") })} /></td>
                    <td style={{ width: 80 }}><input className="input" inputMode="numeric" placeholder={String(product.min_stock)} value={e.min_stock} onChange={(x) => upd({ min_stock: x.target.value.replace(/\D/g, "") })} /></td>
                    <td><input type="checkbox" aria-label="Faol" checked={e.is_active} onChange={(x) => upd({ is_active: x.target.checked })} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <h3 style={{ margin: "8px 0 0" }}>Yangi rang yoki o'lcham qo'shish</h3>
        <div className="row" style={{ gap: 8 }}>
          {colors.map((c) => <button type="button" key={c.id} className={`chip ${newColors.includes(c.id) ? "on" : ""}`} onClick={() => setNewColors(toggle(newColors, c.id))}>{c.name}</button>)}
        </div>
        <div className="row" style={{ gap: 8 }}>
          {sizes.map((c) => <button type="button" key={c.id} className={`chip ${newSizes.includes(c.id) ? "on" : ""}`} onClick={() => setNewSizes(toggle(newSizes, c.id))}>{c.name}</button>)}
        </div>
        <p className="muted" style={{ margin: 0 }}>Tanlangan rang × o'lchamlardan faqat hali yo'q kombinatsiyalar yaratiladi.</p>
      </div>

      <div className="row"><button className="btn btn-primary" disabled={busy} onClick={save}>{busy ? "Saqlanmoqda..." : "Saqlash"}</button></div>
    </div>
  );
}
