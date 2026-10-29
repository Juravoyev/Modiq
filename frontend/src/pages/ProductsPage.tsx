import { Fragment, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { api, qs } from "../api/client";
import type { Page, Product } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorBox, Loading, Pagination, ProductThumb, StockBadge } from "../components/ui";
import { money } from "../utils/format";
import { useAsync, useDebounced } from "../utils/useAsync";

export function ProductsPage() {
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const { branch, isManager } = useAuth();
  const [query, setQuery] = useState("");
  const search = useDebounced(query.trim());
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<number | null>(null);

  const { data, error, loading, reload } = useAsync(
    () => api<Page<Product>>(`/catalog/products/${qs({ search, page, branch: branch?.id })}`),
    [search, page, branch?.id],
  );

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Tovarlar</h1>
        {isManager && <Link className="btn btn-primary" to="/products/new">+ Yangi tovar</Link>}
      </div>
      {notice && <div className="alert alert-warn"><span aria-hidden="true">▲</span> {notice}</div>}
      <input className="input" type="search" placeholder="Nomi, artikul yoki SKU" value={query}
             onChange={(e) => { setQuery(e.target.value); setPage(1); }} aria-label="Qidirish" />
      <div className="card" style={{ padding: 0 }}>
        {loading ? <Loading /> : error ? <div style={{ padding: 16 }}><ErrorBox message={error} onRetry={reload} /></div> :
          !data?.results.length ? (
            <Empty title={search ? "Hech narsa topilmadi" : "Hali tovar qo'shilmagan"}
                   hint={search ? undefined : "Birinchi tovarni rang va o'lchamlari bilan qo'shing."}
                   action={!search && isManager ? <Link className="btn btn-primary" to="/products/new">+ Yangi tovar</Link> : undefined} />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>Tovar</th><th>Artikul</th><th className="right">Sotuv narxi</th><th className="right">Qoldiq ({branch?.name})</th><th>Variantlar</th></tr>
                </thead>
                <tbody>
                  {data.results.map((p) => (
                    <Fragment key={p.id}>
                      <tr style={{ cursor: "pointer" }} onClick={() => setOpen(open === p.id ? null : p.id)}>
                        <td>
                          <div className="row" style={{ gap: 10, flexWrap: "nowrap" }}>
                            <span aria-hidden="true">{open === p.id ? "▾" : "▸"}</span>
                            <ProductThumb src={p.image} alt={p.name} />
                            <span><b>{p.name}</b>
                              {!p.is_active && <span className="badge badge-neutral" style={{ marginLeft: 6 }}>Nofaol</span>}</span>
                          </div>
                        </td>
                        <td>{p.article}</td>
                        <td className="right num">{money(p.sale_price)}</td>
                        <td className="right num">{p.total_stock}</td>
                        <td>{p.variants.length}</td>
                      </tr>
                      {open === p.id && (
                        <tr>
                          <td colSpan={5} style={{ background: "var(--bg)" }}>
                            {isManager && (
                              <div style={{ marginBottom: 12 }}>
                                <Link className="btn btn-secondary btn-sm" to={`/products/${p.id}/edit`}>✎ Tahrirlash</Link>
                              </div>
                            )}
                            {p.variants.length === 0 ? <span className="muted">Variantlar yo'q</span> : (
                              <table className="table">
                                <thead><tr><th>SKU</th><th>Rang</th><th>O'lcham</th><th className="right">Narx</th><th className="right">Qoldiq</th><th>Holat</th></tr></thead>
                                <tbody>
                                  {p.variants.map((v) => (
                                    <tr key={v.id}>
                                      <td>{v.sku}</td><td>{v.color_name}</td><td>{v.size_name}</td>
                                      <td className="right num">{money(v.effective_sale_price)}</td>
                                      <td className="right num">{v.stock ?? 0}</td>
                                      <td><StockBadge quantity={v.stock ?? 0} min={v.effective_min_stock} /></td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            )}
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
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  );
}
