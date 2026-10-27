import { Link } from "react-router-dom";

import { api, qs } from "../api/client";
import type { Dashboard } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { RiskBadge } from "../components/StatusBadge";
import { ErrorBox, Loading } from "../components/ui";
import { WeeklySummaryCard } from "../components/WeeklySummaryCard";
import { dateTime, money } from "../utils/format";
import { useAsync } from "../utils/useAsync";

function Kpi({ label, value, hint, tone, formula }: { label: string; value: string | number; hint?: string; tone?: "warn" | "danger"; formula?: string }) {
  return (
    <div className={`card kpi ${tone ?? ""}`} title={formula}>
      <span className="kpi-label">{label}{formula && <span aria-label={formula} className="muted">ⓘ</span>}</span>
      <span className="kpi-value">{value}</span>
      {hint && <span className="kpi-hint">{hint}</span>}
    </div>
  );
}

export function DashboardPage() {
  const { branch, isManager } = useAuth();
  const { data, error, loading, reload } = useAsync(
    () => api<Dashboard>(`/reports/dashboard/${qs({ branch: branch?.id })}`), [branch?.id],
  );
  if (loading) return <Loading />;
  if (error || !data) return <ErrorBox message={error ?? "Xatolik"} onRetry={reload} />;
  const f = data.formulas;

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Bosh sahifa · {branch?.name}</h1>
        <span className="muted">Bugun, {data.date.split("-").reverse().join(".")}</span>
      </div>

      <div className="kpis">
        <Kpi label="Bugungi tushum" value={money(data.revenue)} formula={f.revenue}
             hint={Number(data.returns_total) > 0 ? `Qaytarilgan: ${money(data.returns_total)}` : undefined} />
        <Kpi label="Savdolar soni" value={data.sales_count} hint={`${data.items_sold} dona sotildi`} formula={f.sales_count} />
        {isManager && data.gross_profit !== undefined && (
          <Kpi label="Taxminiy yalpi foyda" value={money(data.gross_profit)} hint="Sof foyda emas" formula={f.gross_profit} />
        )}
        <Kpi label="Umumiy qoldiq" value={`${data.stock_units} dona`} formula={f.stock_units}
             hint={isManager && data.stock_value ? `Tannarxda: ${money(data.stock_value)}` : undefined} />
        <Kpi label="Kam qolgan variantlar" value={data.low_stock_count} tone={data.low_stock_count ? "warn" : undefined} formula={f.low_stock} />
        <Kpi label="Xavfli tovarlar" value={data.risky_count} tone={data.risky_count ? "danger" : undefined} formula={f.risky}
             hint="Sotilmay qolish, ortiqcha zaxira yoki mavsumiy xavf" />
      </div>

      {isManager && <WeeklySummaryCard branchId={branch?.id} />}

      <div className="grid-2">
        <div className="card">
          <div className="spread"><h2 style={{ margin: 0 }}>Muhim ogohlantirishlar</h2><Link to="/insights">Barchasi ›</Link></div>
          {data.alerts.length === 0 ? <p className="muted">Yuqori darajali xavf yo'q.</p> : data.alerts.map((a, i) => (
            <div key={i} className="list-row" style={{ flexDirection: "column", gap: 4 }}>
              <div className="spread"><b>{a.product_name} · {a.variant_name}</b><RiskBadge level={a.level} /></div>
              <span className="muted">{a.title} · {a.branch_name}</span>
              <span style={{ fontSize: 13 }}>{a.reason}</span>
            </div>
          ))}
        </div>

        <div className="stack">
          <div className="card">
            <div className="spread"><h2 style={{ margin: 0 }}>Kam qolgan o'lcham va ranglar</h2><Link to="/stock">Qoldiq ›</Link></div>
            {data.low_stock.length === 0 ? <p className="muted">Hammasi yetarli.</p> : data.low_stock.map((s) => (
              <div key={`${s.sku}-${s.branch_name}`} className="list-row">
                <span>{s.product_name} · {s.variant_name}<div className="muted">{s.sku}</div></span>
                <span className={s.quantity === 0 ? "badge badge-danger" : "badge badge-warn"}>
                  {s.quantity === 0 ? "✕ Tugagan" : `▲ ${s.quantity} / ${s.min_stock}`}
                </span>
              </div>
            ))}
          </div>
          <div className="card">
            <div className="spread"><h2 style={{ margin: 0 }}>So'nggi savdolar</h2><Link to="/sales">Barchasi ›</Link></div>
            {data.recent_sales.length === 0 ? <p className="muted">Hali savdo yo'q.</p> : data.recent_sales.map((s) => (
              <div key={s.id} className="list-row">
                <span>№ {s.id} · {dateTime(s.created_at)}<div className="muted">{s.branch_name} · {s.items} dona</div></span>
                <b className="num">{money(s.total)}</b>
              </div>
            ))}
          </div>
        </div>
      </div>
      <p className="muted">ⓘ belgisi ustiga kursor olib borsangiz, ko'rsatkich qanday hisoblanishi ko'rinadi.</p>
    </div>
  );
}
