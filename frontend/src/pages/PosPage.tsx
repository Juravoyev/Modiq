import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { api, ApiError, qs } from "../api/client";
import type { CustomerBrief, Page, PaymentType, Quote, Sale, Variant } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CustomerPicker } from "../components/CustomerPicker";
import { Receipt } from "../components/Receipt";
import { Empty, ErrorBox, PageHeader, ProductThumb } from "../components/ui";
import { money, newIdempotencyKey } from "../utils/format";
import { useAsync, useDebounced } from "../utils/useAsync";
import { Icon } from "../components/Icon";

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
  const [customer, setCustomerState] = useState<CustomerBrief | null>(null);
  const [bonusInput, setBonusInput] = useState("");
  const [payment, setPayment] = useState<PaymentType>("cash");
  // Kalit savat o'zgargandagina yangilanadi: tarmoq xatosidan keyin "qayta urinish" o'sha savdoni takrorlamaydi.
  const [idemKey, setIdemKey] = useState(newIdempotencyKey);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needBelowCostConfirm, setNeedBelowCostConfirm] = useState(false);
  const [belowCostConfirmed, setBelowCostConfirmed] = useState(false);
  const [done, setDone] = useState<Sale | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const cartRef = useRef<HTMLElement>(null);

  // Yakuniy narxni (aksiya, imtiyoz, chegirma) backend hisoblaydi: savdo yakunlanganda ham aynan shu qoidalar ishlaydi.
  const cartKey = JSON.stringify({
    customer: customer?.id ?? null,
    bonus: customer ? Number(bonusInput || 0) : 0,
    lines: cart.map((l) => [l.variant.id, l.quantity, l.discount || "0"]),
  });
  const quoteKey = useDebounced(cartKey, 300);
  const [quote, setQuote] = useState<{ key: string; data: Quote | null; error: ApiError | null } | null>(null);

  useEffect(() => {
    const parsed = JSON.parse(quoteKey) as { customer: number | null; bonus: number; lines: [number, number, string][] };
    if (!branch || parsed.lines.length === 0) { setQuote(null); return; }
    let alive = true;
    const lines = parsed.lines.map(([variant, quantity, discount_amount]) => ({ variant, quantity, discount_amount }));
    api<Quote>("/sales/quote/", { method: "POST", body: { branch: branch.id, customer: parsed.customer, bonus_to_use: parsed.bonus, lines } })
      .then((data) => alive && setQuote({ key: quoteKey, data, error: null }))
      .catch((error: ApiError) => alive && setQuote({ key: quoteKey, data: null, error }));
    return () => { alive = false; };
  }, [quoteKey, branch]);

  const fresh = quote && quote.key === cartKey ? quote : null;
  // Bonus chegarasi so'nggi muvaffaqiyatli hisobdan olinadi (summa oshib xato bo'lsa ham ko'rinib turadi).
  const [bonusInfo, setBonusInfo] = useState<Quote["bonus"] | null>(null);
  useEffect(() => {
    if (quote?.data) setBonusInfo(quote.data.customer ? quote.data.bonus : null);
  }, [quote]);
  useEffect(() => { if (!customer) setBonusInfo(null); }, [customer]);
  const quoteLine = (id: number) => fresh?.data?.lines.find((l) => l.variant === id);

  // Qidiruv bo'sh bo'lsa, tovarlarning birinchi sahifasi ko'rsatiladi: bosib savatga qo'shish mumkin.
  const results = useAsync(
    () => api<Page<Variant>>(`/catalog/variants/${qs({ search: search || undefined, branch: branch?.id, is_active: true, page_size: 24 })}`),
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

  function setCustomer(c: CustomerBrief | null) {
    setCustomerState(c);
    setBonusInput("");
    setIdemKey(newIdempotencyKey());
    setError(null);
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
    if (e.key === "Enter" && search && !results.loading && results.data?.results.length === 1) add(results.data.results[0]);
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
    const q = fresh?.data;
    if (q) return { subtotal: Number(q.subtotal), discount: Number(q.discount_total), total: Number(q.total), invalid };
    return { subtotal, discount, total: subtotal - discount, invalid };
  }, [cart, fresh]);

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
          customer: customer?.id ?? null,
          bonus_to_use: customer ? Number(bonusInput || 0) : 0,
          lines: cart.map((l) => ({ variant: l.variant.id, quantity: l.quantity, discount_amount: l.discount || "0" })),
        },
      });
      setDone(sale);
      results.reload(); // qoldiqlar o'zgardi
      setCart([]);
      setCustomerState(null);
      setBonusInput("");
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
        <div className="sale-done no-print" role="status">
          <span className="sale-done-icon"><Icon name="check" size={28} /></span>
          <h1>Savdo yakunlandi</h1>
          <span className="muted">Chek № {done.id} · {money(done.total)}</span>
        </div>
        <div className="card"><Receipt sale={done} businessName={me?.business.name ?? ""} /></div>
        <div className="row no-print">
          <button className="btn btn-secondary grow" onClick={() => window.print()}><Icon name="printer" size={17} /> Chop etish</button>
          <button className="btn btn-primary grow" onClick={() => setDone(null)}><Icon name="plus" size={17} /> Yangi savdo</button>
        </div>
      </div>
    );
  }

  return (
    <div className="pos">
      <section className="stack">
        <PageHeader title="Kassa" subtitle={branch?.name} />
        <div className="search-box">
          <Icon name="search" size={20} />
          <input
            ref={searchRef} className="input" type="search"
            placeholder="SKU, shtrix-kod yoki tovar nomi" value={query} onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onSearchKey} aria-label="Tovar qidirish"
          />
        </div>
        {results.error ? (
          <ErrorBox message={results.error} onRetry={results.reload} />
        ) : !results.data ? (
          <div className="product-grid" aria-hidden="true">
            {Array.from({ length: 8 }, (_, i) => <div key={i} className="product-card skeleton" />)}
          </div>
        ) : !results.data.results.length ? (
          search
            ? <Empty title="Hech narsa topilmadi" hint="Boshqa so'z yoki SKU bilan qidirib ko'ring." />
            : <Empty title="Hali tovar yo'q" hint="Tovarlar bo'limida birinchi tovarni qo'shing." />
        ) : (
          <>
            <p className="muted">
              {search ? `Topildi: ${results.data.count} ta` : "Tovarni bosing, qidiring yoki shtrix-kodni skaner qiling."}
            </p>
            <div className={`product-grid ${results.loading ? "is-loading" : ""}`}>
              {results.data.results.map((v) => {
                const stock = v.stock ?? 0;
                const inCart = cart.find((l) => l.variant.id === v.id)?.quantity ?? 0;
                return (
                  <button key={v.id} className={`product-card ${inCart ? "in-cart" : ""}`} onClick={() => add(v)} disabled={stock <= 0}>
                    <span className="product-card-media">
                      {v.product_image
                        ? <img src={v.product_image} alt="" loading="lazy" />
                        : <Icon name="shirt" size={36} />}
                      {inCart > 0 && <span className="product-card-count num" aria-label={`Savatda ${inCart} dona`}>{inCart}</span>}
                    </span>
                    <span className="product-card-body">
                      <span className="product-card-name">{v.product_name}</span>
                      <span className="muted">{v.color_name} · {v.size_name}</span>
                      <span className="product-card-foot">
                        <b className="num">{money(v.effective_sale_price)}</b>
                        <span className={stock > 0 ? "muted num" : "field-error"}>{stock > 0 ? `${stock} dona` : "Tugagan"}</span>
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </>
        )}
      </section>

      <aside className="card pos-cart stack" ref={cartRef}>
        <div className="spread">
          <h2>Savat {cart.length > 0 && <span className="badge badge-ok num">{cart.reduce((n, l) => n + l.quantity, 0)}</span>}</h2>
          {cart.length > 0 && <button className="btn btn-secondary btn-sm" onClick={() => changeCart([])}>Tozalash</button>}
        </div>
        {cart.length === 0 ? (
          <div className="cart-empty">
            <Icon name="cart" size={28} />
            <b>Savat bo'sh</b>
            <span className="muted">Tovarni bosing yoki shtrix-kodni skaner qiling</span>
          </div>
        ) : (
          <div>
            {cart.map((l) => {
              const gross = Number(l.variant.effective_sale_price) * l.quantity;
              const bad = Number(l.discount || 0) > gross;
              const ql = quoteLine(l.variant.id);
              const lineTotal = ql ? Number(ql.line_total) : gross - Number(l.discount || 0);
              return (
                <div key={l.variant.id} className="cart-line stack gap-2">
                  <div className="cart-line-head">
                    <ProductThumb src={l.variant.product_image} size={44} />
                    <div className="grow">
                      <div className="bold">{l.variant.product_name}</div>
                      <div className="muted">{l.variant.color_name} · {l.variant.size_name} · {money(l.variant.effective_sale_price)}</div>
                    </div>
                    <button className="icon-btn" aria-label="O'chirish" title="O'chirish"
                            onClick={() => changeCart(cart.filter((x) => x.variant.id !== l.variant.id))}><Icon name="x" size={16} /></button>
                  </div>
                  <div className="spread">
                    <div className="qty">
                      <button onClick={() => setQty(l.variant.id, l.quantity - 1)} aria-label="Kamaytirish" disabled={l.quantity <= 1}><Icon name="minus" size={16} /></button>
                      <span className="num">{l.quantity}</span>
                      <button onClick={() => setQty(l.variant.id, l.quantity + 1)} aria-label="Ko'paytirish"
                              disabled={l.quantity >= (l.variant.stock ?? 0)}><Icon name="plus" size={16} /></button>
                    </div>
                    <span className="num right">
                      {lineTotal !== gross && <s className="muted" style={{ display: "block" }}>{money(gross)}</s>}
                      <b>{money(lineTotal)}</b>
                    </span>
                  </div>
                  {ql && Number(ql.auto_discount) > 0 && (
                    <span className="badge badge-ok" style={{ alignSelf: "flex-start", whiteSpace: "normal" }}>
                      <Icon name="tag" size={13} /> {ql.discount_label}: −{money(ql.auto_discount)}
                    </span>
                  )}
                  <input className={`input ${bad ? "invalid" : ""}`} inputMode="decimal" placeholder={!isManager && fresh?.data
                           ? `Qo'shimcha chegirma (ko'pi bilan ${fresh.data.cashier_max_discount_percent}%)`
                           : "Qo'shimcha chegirma (so'm)"}
                         value={l.discount} onChange={(e) => setDiscount(l.variant.id, e.target.value)}
                         aria-label="Chegirma summasi" />
                  {bad && <span className="field-error">Chegirma narxdan katta bo'lishi mumkin emas.</span>}
                </div>
              );
            })}
          </div>
        )}

        <CustomerPicker value={customer} onChange={setCustomer} />
        {customer && bonusInfo?.enabled && (
          <div className="stack gap-2">
            <div className="spread">
              <span className="row gap-2"><Icon name="gift" size={16} /> Bonus: <b className="num">{money(bonusInfo.available)}</b></span>
              {Number(bonusInfo.pending) > 0 && (
                <span className="muted">+{money(bonusInfo.pending)} 24 soatdan keyin</span>
              )}
            </div>
            {Number(bonusInfo.available) > 0 && (
              <div className="row gap-2 nowrap">
                <input className="input" inputMode="numeric" placeholder={`Bonusdan to'lash (ko'pi bilan ${money(bonusInfo.max)})`}
                       value={bonusInput} aria-label="Bonusdan to'lanadigan summa"
                       onChange={(e) => { setBonusInput(e.target.value.replace(/[^\d]/g, "")); setIdemKey(newIdempotencyKey()); }} />
                <button className="btn btn-secondary" disabled={Number(bonusInfo.max) <= 0}
                        onClick={() => { setBonusInput(String(Math.floor(Number(bonusInfo.max)))); setIdemKey(newIdempotencyKey()); }}>
                  Maksimal
                </button>
              </div>
            )}
            <span className="muted">
              Chekning ko'pi bilan {bonusInfo.max_share_percent}% bonus bilan to'lanadi. Har xariddan {bonusInfo.percent}% bonus yig'iladi.
            </span>
          </div>
        )}

        <div className="totals">
          <div className="total-row num"><span>Summa</span><span>{money(totals.subtotal)}</span></div>
          <div className="total-row num"><span>Chegirma</span><span>{totals.discount > 0 ? `−${money(totals.discount)}` : money(0)}</span></div>
          {fresh?.data && Number(fresh.data.bonus.used) > 0 && (
            <div className="total-row num"><span>Bonus bilan</span><span>−{money(fresh.data.bonus.used)}</span></div>
          )}
          <div className="total-row big num"><span>Jami</span><span>{money(totals.total)}</span></div>
          {fresh?.data && Number(fresh.data.bonus.earned) > 0 && (
            <div className="total-row num muted"><span>Bu xariddan bonus</span><span>+{money(fresh.data.bonus.earned)}</span></div>
          )}
        </div>

        <div className="segmented" role="radiogroup" aria-label="To'lov turi">
          {PAYMENTS.map((p) => (
            <button key={p.value} role="radio" aria-checked={payment === p.value}
                    className={payment === p.value ? "on" : ""} onClick={() => setPayment(p.value)}>
              {p.label}
            </button>
          ))}
        </div>

        {error && <ErrorBox message={error} />}
        {!error && fresh?.error && <ErrorBox message={fresh.error.message} />}
        {needBelowCostConfirm && (
          <label className="alert alert-warn clickable">
            <input type="checkbox" checked={belowCostConfirmed} onChange={(e) => setBelowCostConfirmed(e.target.checked)} />
            Narx xarid narxidan past ekanini bilaman va tasdiqlayman.
          </label>
        )}

        <button className="btn btn-primary btn-lg" onClick={complete}
                disabled={busy || cart.length === 0 || totals.invalid.length > 0 || !fresh?.data ||
                          (needBelowCostConfirm && !belowCostConfirmed)}>
          {busy ? "Bajarilmoqda..." : cart.length > 0 && !fresh ? "Hisoblanmoqda..." : `Savdoni yakunlash · ${money(totals.total)}`}
        </button>
      </aside>

      {cart.length > 0 && (
        <button className="cart-bar no-print" onClick={() => cartRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}>
          <span className="row gap-2"><Icon name="cart" size={20} /> Savat · {cart.reduce((n, l) => n + l.quantity, 0)} dona</span>
          <b className="num">{money(totals.total)}</b>
        </button>
      )}
    </div>
  );
}
