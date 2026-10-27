import { useState } from "react";

import { api, qs } from "../api/client";
import type { Page, Variant } from "../api/types";
import { useAsync, useDebounced } from "../utils/useAsync";
import { Loading } from "./ui";

/** Variantni SKU yoki nom bo'yicha qidirib tanlash (kirim, ko'chirish, inventarizatsiya uchun). */
export function VariantPicker({ branchId, onPick, label = "Tovar qo'shish" }: {
  branchId?: number; onPick: (v: Variant) => void; label?: string;
}) {
  const [query, setQuery] = useState("");
  const search = useDebounced(query.trim());
  const results = useAsync(
    () => (search ? api<Page<Variant>>(`/catalog/variants/${qs({ search, branch: branchId })}`) : Promise.resolve(null)),
    [search, branchId],
  );
  return (
    <div className="stack" style={{ gap: 6 }}>
      <label className="field">
        <span className="field-label">{label}</span>
        <input className="input" type="search" placeholder="SKU yoki tovar nomi" value={query}
               onChange={(e) => setQuery(e.target.value)} />
      </label>
      {search && (results.loading ? <Loading text="Qidirilmoqda..." /> : (
        <div className="stack" style={{ gap: 6 }}>
          {results.data?.results.map((v) => (
            <button type="button" key={v.id} className="result-item" onClick={() => { onPick(v); setQuery(""); }}>
              <span>{v.product_name} · {v.color_name} · {v.size_name}</span>
              <span className="muted">{v.sku} · {v.stock ?? 0} dona</span>
            </button>
          ))}
          {results.data && !results.data.results.length && <span className="muted">Topilmadi</span>}
        </div>
      ))}
    </div>
  );
}
