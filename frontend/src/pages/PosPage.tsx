import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { api, ApiError, qs } from "../api/client";
import type { Page, PaymentType, Sale, Variant } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Receipt } from "../components/Receipt";
import { Empty, ErrorBox, Loading } from "../components/ui";
import { money, newIdempotencyKey } from "../utils/format";
import { useAsync, useDebounced } from "../utils/useAsync";

interface CartLine { variant: Variant; quantity: number; discount: string }

const PAYMENTS: { value: PaymentType; label: string }[] = [
  { value: "cash", label: "Naqd" },
  { value: "card", label: "Karta" },
  { value: "online", label: "Onlayn" },
];

export function PosPage() {
  const { branch, me, isManager } = useAuth();
  const [query, setQuery] = useState("");
  const search = useDebounced(query.trim(), 250);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [payment, setPayment] = useState<PaymentType>("cash");
  // Kalit savat o'zgargandagina yangilanadi: tarmoq xatosidan keyin "qayta urinish" o'sha savdoni takrorlamaydi.
  const [idemKey, setIdemKey] = useState(newIdempotencyKey);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needBelowCostConfirm, setNeedBelowCostConfirm] = useState(false);
  const [belowCostConfirmed, setBelowCostConfirmed] = useState(false);
  const [done, setDone] = useState<Sale | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const results = useAsync(
    () => search
      ? api<Page<Variant>>(`/catalog/variants/${qs({ search, branch: branch?.id, is_active: true })}`)
      : Promise.resolve(null),
    [search, branch?.id],
  );

  useEffect(() => { searchRef.current?.focus(); }, [done]);

  function changeCart(next: CartLine[]) {
    setCart(next);
    setIdemKey(newIdempotencyKey());
    setError(null);
    setNeedBelowCostConfirm(false);
    setBelowCostConfirmed(false);
  }

  function add(v: Variant) {
    const stock = v.stock ?? 0;
    const existing = cart.find((l) => l.variant.id === v.id);
    if (existing) {
      if (existing.quantity >= stock) return setError(`${v.sku}: qoldiqda faqat ${stock} dona bor.`);
      changeCart(cart.map((l) => (l.variant.id === v.id ? { ...l, quantity: l.quantity + 1 } : l)));
    } else {
      if (stock <= 0) return setError(`${v.sku}: qoldiqda yo'q.`);
      changeCart([...cart, { variant: v, quantity: 1, discount: "" }]);
    }
    setQuery("");
    searchRef.current?.focus();
  }

  function onSearchKey(e: KeyboardEvent<HTMLInputElement>) {
    // Shtrix-kod skaneri Enter yuboradi: bitta natija bo'lsa, darhol savatga qo'shiladi.
    if (e.key === "Enter" && results.data?.results.length === 1) add(results.data.results[0]);
  }

  const setQty = (id: number, q: number) =>
    changeCart(cart.map((l) => (l.variant.id === id ? { ...l, quantity: Math.max(1, Math.min(q, l.variant.stock ?? q)) } : l)));
  const setDiscount = (id: number, d: string) =>
    changeCart(cart.map((l) => (l.variant.id === id ? { ...l, discount: d.replace(/[^\d.]/g, "") } : l)));

  const totals = useMemo(() => {
    let subtotal = 0;
    let discount = 0;
    const invalid: string[] = [];
    for (const l of cart) {
      const gross = Number(l.variant.effective_sale_price) * l.quantity;
      const d = Number(l.discount || 0);
      if (d > gross) invalid.push(l.variant.sku);
      subtotal += gross;
      discount += d;
    }
    return { subtotal, discount, total: subtotal - discount, invalid };
  }, [cart]);

  async function complete() {
    if (!branch || cart.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const sale = await api<Sale>("/sales/", {
        method: "POST",
        body: {
          idempotency_key: idemKey,
          branch: branch.id,
          payment_type: payment,
          allow_below_cost: belowCostConfirmed,
          lines: cart.map((l) => ({ variant: l.variant.id, quantity: l.quantity, discount_amount: l.discount || "0" })),
        },
      });
      setDone(sale);
      setCart([]);
      setPayment("cash");
      setIdemKey(newIdempotencyKey());
      setNeedBelowCostConfirm(false);
      setBelowCostConfirmed(false);
    } catch (err) {
      const e = err as ApiError;
      if (e.code === "below_cost" && isManager) setNeedBelowCostConfirm(true);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="stack" style={{ maxWidth: 420, margin: "0 auto" }}>
        <div className="alert alert-success no-print"><span aria-hidden="true">✓</span> Savdo yakunlandi</div>
        <div className="card"><Receipt sale={done} businessName={me?.business.name ?? ""} /></div>
        <div className="row no-print">
          <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => window.print()}>Chop etish</button>
          <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => setDone(null)}>Yangi savdo</button>
        </div>
      </div>
    );
  }

  return (
    <div className="pos">
      <section className="stack">
        <h1>Kassa</h1>
        <input
          ref={searchRef} className="input" style={{ minHeight: 50, fontSize: 16 }} type="search"
          placeholder="SKU, shtrix-kod yoki tovar nomi" value={query} onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onSearchKey} aria-label="Tovar qidirish"
        />
        {!search ? (
          <p className="muted">Tovarni qidiring yoki shtrix-kodni skaner qiling.</p>
        ) : results.loading ? (
          <Loading text="Qidirilmoqda..." />
        ) : results.error ? (
          <ErrorBox message={results.error} onRetry={results.reload} />
        ) : !results.data?.results.length ? (
          <Empty title="Hech narsa topilmadi" hint="Boshqa so'z yoki SKU bilan qidirib ko'ring." />
        ) : (
          <div className="stack" style={{ gap: 8 }}>
            {results.data.results.map((v) => {
              const stock = v.stock ?? 0;
              return (
                <button key={v.id} className="result-item" onClick={() => add(v)} disabled={stock <= 0}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{v.product_name}</div>
                    <div className="muted">{v.color_name} · {v.size_name} · {v.sku}</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div className="num" style={{ fontWeight: 600 }}>{money(v.effective_sale_price)}</div>
                    <div className={stock > 0 ? "muted" : "field-error"}>{stock > 0 ? `${stock} dona` : "Qoldiqda yo'q"}</div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </section>

      <aside className="card pos-cart stack">
        <div className="spread">
          <h2 style={{ margin: 0 }}>Savat</h2>
          {cart.length > 0 && <button className="btn btn-secondary btn-sm" onClick={() => changeCart([])}>Tozalash</button>}
        </div>
        {cart.length === 0 ? (
          <p className="muted">Savat bo'sh</p>
        ) : (
          <div>
            {cart.map((l) => {
              const gross = Number(l.variant.effective_sale_price) * l.quantity;
              const bad = Number(l.discount || 0) > gross;
              return (
                <div key={l.variant.id} className="cart-line stack" style={{ gap: 6 }}>
                  <div className="spread">
                    <div>
                      <div style={{ fontWeight: 600 }}>{l.variant.product_name}</div>
                      <div className="muted">{l.variant.color_name} · {l.variant.size_name}</div>
                    </div>
                    <button className="btn btn-secondary btn-sm" aria-label="O'chirish"
                            onClick={() => changeCart(cart.filter((x) => x.variant.id !== l.variant.id))}>✕</button>
                  </div>
                  <div className="spread">
                    <div className="qty">
                      <button onClick={() => setQty(l.variant.id, l.quantity - 1)} aria-label="Kamaytirish">−</button>
                      <span className="num">{l.quantity}</span>
                      <button onClick={() => setQty(l.variant.id, l.quantity + 1)} aria-label="Ko'paytirish"
                              disabled={l.quantity >= (l.variant.stock ?? 0)}>+</button>
                    </div>
                    <span className="num" style={{ fontWeight: 600 }}>{money(gross - Number(l.discount || 0))}</span>
                  </div>
                  <input className={`input ${bad ? "invalid" : ""}`} inputMode="decimal" placeholder="Chegirma (so'm)"
                         value={l.discount} onChange={(e) => setDiscount(l.variant.id, e.target.value)}
                         aria-label="Chegirma summasi" />
                  {bad && <span className="field-error">Chegirma narxdan katta bo'lishi mumkin emas.</span>}
                </div>
              );
            })}
          </div>
        )}

        <div>
          <div className="total-row num"><span>Summa</span><span>{money(totals.subtotal)}</span></div>
          <div className="total-row num"><span>Chegirma</span><span>{totals.discount > 0 ? `−${money(totals.discount)}` : money(0)}</span></div>
          <div className="total-row big num"><span>Jami</span><span>{money(totals.total)}</span></div>
        </div>

        <div className="row" role="radiogroup" aria-label="To'lov turi">
          {PAYMENTS.map((p) => (
            <button key={p.value} role="radio" aria-checked={payment === p.value}
                    className={`chip ${payment === p.value ? "on" : ""}`} onClick={() => setPayment(p.value)}>
              {p.label}
            </button>
          ))}
        </div>

        {error && <ErrorBox message={error} />}
        {needBelowCostConfirm && (
          <label className="alert alert-warn" style={{ cursor: "pointer" }}>
            <input type="checkbox" checked={belowCostConfirmed} onChange={(e) => setBelowCostConfirmed(e.target.checked)} />
            Narx xarid narxidan past ekanini bilaman va tasdiqlayman.
          </label>
        )}

        <button className="btn btn-primary btn-lg" onClick={complete}
                disabled={busy || cart.length === 0 || totals.invalid.length > 0 || (needBelowCostConfirm && !belowCostConfirmed)}>
          {busy ? "Bajarilmoqda..." : `Savdoni yakunlash · ${money(totals.total)}`}
        </button>
      </aside>
    </div>
  );
}
