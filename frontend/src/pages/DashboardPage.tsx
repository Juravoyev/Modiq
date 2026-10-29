import { useState } from "react";
import { Link } from "react-router-dom";

import { api, qs } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorBox, Loading } from "../components/ui";
import { money } from "../utils/format";
import { useAsync } from "../utils/useAsync";

interface Dashboard {
  days: number;
  today: { revenue: string; sales_count: number; avg_check: string; refunds: string };
  period: {
    revenue: string; sales_count: number; avg_check: string; refunds: string; returns_count: number;
    written_off: string; net_revenue: string; cost: string; gross_profit: string;
  };
  daily: { date: string; revenue: string; count: number }[];
  payments: { payment_type: string; label: string; revenue: string; count: number }[];
  top_products: { product_id: number; name: string; quantity: number; revenue: string }[];
  slow_movers: { product_id: number; name: string; article: string; units: number; value: string }[];
  stock: { units: number; value: string; low_count: number };
  pending_returns: number;
}

function Tile({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "warn" }) {
  return (
    <div className="card tile">
      <div className="muted">{label}</div>
      <div className={`tile-value num ${tone === "warn" ? "tile-warn" : ""}`}>{value}</div>
      {hint && <div className="muted">{hint}</div>}
    </div>
  );
}

const shortDate = (iso: string) => {
  const [, m, d] = iso.split("-");
  return `${d}.${m}`;
};

/** Kunlik tushum: bitta qator, ustiga borilganda kun va summa ko'rinadi. */
function DailyChart({ daily }: { daily: Dashboard["daily"] }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(...daily.map((d) => Number(d.revenue)), 1);
  const labelEvery = Math.ceil(daily.length / 8);
  const h = hover !== null ? daily[hover] : null;

  return (
    <div className="chart">
      <div className="chart-tooltip num" aria-live="polite">
        {h ? <><b>{shortDate(h.date)}</b> · {money(h.revenue)} · {h.count} ta savdo</> : <span className="muted">Kunni tanlang</span>}
      </div>
      <div className="chart-plot" role="img"
           aria-label={`Kunlik tushum, oxirgi ${daily.length} kun. Eng ko'pi ${money(max)}.`}
           onMouseLeave={() => setHover(null)}>
        <div className="chart-gridline" style={{ bottom: "100%" }}><span>{money(max)}</span></div>
        <div className="chart-gridline" style={{ bottom: "50%" }}><span>{money(max / 2)}</span></div>
        {daily.map((d, i) => (
          <div key={d.date} className={`chart-col ${hover === i ? "on" : ""}`}
               onMouseEnter={() => setHover(i)} onClick={() => setHover(i)}
               title={`${shortDate(d.date)}: ${money(d.revenue)}`}>
            <div className="chart-bar" style={{ height: `${(Number(d.revenue) / max) * 100}%` }} />
          </div>
        ))}
      </div>
      <div className="chart-axis">
        {daily.map((d, i) => <span key={d.date}>{i % labelEvery === 0 || i === daily.length - 1 ? shortDate(d.date) : ""}</span>)}
      </div>
    </div>
  );
}

const PERIODS = [7, 30, 90];

export function DashboardPage() {
  const { branch, me } = useAuth();
  const [days, setDays] = useState(30);
  const [allBranches, setAllBranches] = useState(false);
  const { data, error, loading, reload } = useAsync(
    () => api<Dashboard>(`/sales/dashboard/${qs({ days, branch: allBranches ? undefined : branch?.id })}`),
    [days, allBranches, branch?.id],
  );
  const multi = (me?.branches.length ?? 0) > 1;

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Hisobot · {allBranches ? "barcha filiallar" : branch?.name}</h1>
        <div className="row" style={{ gap: 8 }}>
          {multi && (
            <button className={`chip ${allBranches ? "on" : ""}`} aria-pressed={allBranches} onClick={() => setAllBranches(!allBranches)}>
              Barcha filiallar
            </button>
          )}
          <div className="row" role="radiogroup" aria-label="Davr" style={{ gap: 6 }}>
            {PERIODS.map((p) => (
              <button key={p} role="radio" aria-checked={days === p} className={`chip ${days === p ? "on" : ""}`} onClick={() => setDays(p)}>
                {p} kun
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading && !data ? <Loading /> : error || !data ? <ErrorBox message={error ?? "Xatolik"} onRetry={reload} /> : (
        <>
          {data.pending_returns > 0 && (
            <Link to="/returns" className="alert alert-warn" style={{ textDecoration: "none" }}>
              <span aria-hidden="true">◷</span> {data.pending_returns} ta qaytarish so'rovi tasdiqni kutmoqda ›
            </Link>
          )}

          <h2 style={{ margin: "4px 0 0" }}>Bugun</h2>
          <div className="tiles">
            <Tile label="Tushum" value={money(data.today.revenue)} />
            <Tile label="Savdolar" value={String(data.today.sales_count)} hint={`O'rtacha chek: ${money(data.today.avg_check)}`} />
            <Tile label="Qaytarilgan pul" value={money(data.today.refunds)} />
          </div>

          <h2 style={{ margin: "4px 0 0" }}>Oxirgi {data.days} kun</h2>
          <div className="tiles">
            <Tile label="Tushum" value={money(data.period.revenue)} hint={`${data.period.sales_count} ta savdo · o'rtacha ${money(data.period.avg_check)}`} />
            <Tile label="Taxminiy yalpi foyda" value={money(data.period.gross_profit)}
                  hint="Tushum − qaytarilgan − tannarx. Ijara, maosh hisobga olinmagan" />
            <Tile label="Yaroqsiz tovar (hisobdan chiqarilgan)" value={money(data.period.written_off)}
                  hint={`${data.period.returns_count} ta qaytarish · mijozga ${money(data.period.refunds)}`}
                  tone={Number(data.period.written_off) > 0 ? "warn" : undefined} />
            <Tile label="Ombordagi tovar (tannarxda)" value={money(data.stock.value)}
                  hint={`${data.stock.units} dona · ${data.stock.low_count} ta variant kam qolgan`} />
          </div>

          <div className="card stack">
            <h2 style={{ margin: 0 }}>Kunlik tushum</h2>
            {data.period.sales_count === 0 ? <Empty title="Bu davrda savdo yo'q" /> : <DailyChart daily={data.daily} />}
          </div>

          <div className="grid-2">
            <div className="card stack">
              <h2 style={{ margin: 0 }}>Eng ko'p sotilganlar</h2>
              {!data.top_products.length ? <span className="muted">Savdo yo'q</span> : (
                <table className="table">
                  <thead><tr><th>Tovar</th><th className="right">Dona</th><th className="right">Tushum</th></tr></thead>
                  <tbody>
                    {data.top_products.map((p) => (
                      <tr key={p.product_id}><td>{p.name}</td><td className="right num">{p.quantity}</td><td className="right num">{money(p.revenue)}</td></tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="card stack">
              <h2 style={{ margin: 0 }}>To'lov turlari</h2>
              {!data.payments.length ? <span className="muted">Savdo yo'q</span> : (
                <table className="table">
                  <thead><tr><th>Tur</th><th className="right">Savdolar</th><th className="right">Summa</th></tr></thead>
                  <tbody>
                    {data.payments.map((p) => (
                      <tr key={p.payment_type}><td>{p.label}</td><td className="right num">{p.count}</td><td className="right num">{money(p.revenue)}</td></tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          <div className="card stack">
            <div>
              <h2 style={{ margin: 0 }}>Sotilmay turgan tovarlar</h2>
              <span className="muted">Qoldig'i bor, lekin oxirgi {data.days} kunda bitta ham sotilmagan. Aksiya yoki chegirma uchun nomzodlar.</span>
            </div>
            {!data.slow_movers.length ? <span className="muted">Bunday tovar yo'q, hammasi sotilyapti.</span> : (
              <table className="table">
                <thead><tr><th>Tovar</th><th className="right">Qoldiq</th><th className="right">Tannarxda qiymati</th><th /></tr></thead>
                <tbody>
                  {data.slow_movers.map((p) => (
                    <tr key={p.product_id}>
                      <td>{p.name} <span className="muted">{p.article}</span></td>
                      <td className="right num">{p.units}</td>
                      <td className="right num">{money(p.value)}</td>
                      <td><Link className="btn btn-secondary btn-sm" to={`/products/${p.product_id}/edit`}>Narxni o'zgartirish</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
