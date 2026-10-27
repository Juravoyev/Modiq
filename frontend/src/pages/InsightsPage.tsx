import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api, qs } from "../api/client";
import type { RiskLevel, RiskResponse, RiskType, VariantInsight } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { RiskBadge } from "../components/StatusBadge";
import { Empty, ErrorBox, Loading } from "../components/ui";
import { dateTime } from "../utils/format";
import { useAsync } from "../utils/useAsync";

const TYPES: { value: RiskType | ""; label: string }[] = [
  { value: "", label: "Hammasi" },
  { value: "no_sale", label: "Sotilmay qolish" },
  { value: "overstock", label: "Ortiqcha zaxira" },
  { value: "seasonal", label: "Mavsumiy" },
  { value: "restock", label: "Qayta to'ldirish" },
];

const DISCOUNTABLE: RiskType[] = ["no_sale", "overstock", "seasonal"];

function InsightCard({ item, canDiscount }: { item: VariantInsight; canDiscount: boolean }) {
  return (
    <div className={`card stack risk-card ${item.top_level ?? ""}`} style={{ gap: 8 }}>
      <div className="spread">
        <div>
          <b>{item.product_name}</b> · {item.variant_name}
          <div className="muted">{item.sku} · {item.branch_name}</div>
        </div>
      </div>
      <div className="facts">
        <span>Qoldiq: <b>{item.quantity} dona</b></span>
        <span>Oxirgi sotuv: <b>{item.last_sale_at ? `${dateTime(item.last_sale_at)} (${item.days_since_last_sale} kun oldin)` : "hali sotilmagan"}</b></span>
        <span>Oxirgi {item.window_days} kunda: <b>{item.sold_in_window} dona</b></span>
        <span>Sotuv sur'ati: <b>{item.velocity_per_day !== null ? `kuniga ~${String(item.velocity_per_day).replace(".", ",")} dona` : "ma'lumot yetarli emas"}</b></span>
        {item.days_of_cover !== null && item.quantity > 0 && <span>Qoldiq yetadi: <b>~{item.days_of_cover} kun</b></span>}
        {item.season && <span>Mavsum: <b>{item.season}</b></span>}
      </div>
      {item.risks.map((r, i) => (
        <div key={i} className="stack" style={{ gap: 6, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
          <div className="row" style={{ gap: 8 }}><RiskBadge level={r.level} /> <b>{r.title}</b></div>
          <div><span className="muted">Tavsiya:</span> {r.action}</div>
          <details className="why">
            <summary>Nega bu tavsiya berildi?</summary>
            <div className="why-body">{r.reason}</div>
          </details>
        </div>
      ))}
      {canDiscount && item.risks.some((r) => DISCOUNTABLE.includes(r.type)) && (
        <div><Link className="btn btn-secondary btn-sm" to={`/discounts?variant=${item.variant}`}>Chegirma qo'yish</Link></div>
      )}
    </div>
  );
}

export function InsightsPage() {
  const { branch, isManager } = useAuth();
  const [type, setType] = useState<RiskType | "">("");
  const [level, setLevel] = useState<RiskLevel | "">("");
  const [limit, setLimit] = useState(20);
  const { data, error, loading, reload } = useAsync(
    () => api<RiskResponse>(`/insights/risks/${qs({ branch: branch?.id, type, level })}`), [branch?.id, type, level],
  );
  const shown = useMemo(() => data?.results.slice(0, limit) ?? [], [data, limit]);

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Aqlli tavsiyalar · {branch?.name}</h1>
        {isManager && <Link className="btn btn-secondary btn-sm" to="/settings">Qoidalarni sozlash</Link>}
      </div>
      <p className="muted" style={{ margin: 0 }}>
        Tavsiyalar savdo va qoldiq ma'lumotlari hamda siz belgilagan chegaralar asosida hisoblanadi. Ular qaror
        qabul qilishga yordam beradi, natijani kafolatlamaydi.
      </p>
      <div className="row" style={{ gap: 8 }}>
        {TYPES.map((t) => (
          <button key={t.value} className={`chip ${type === t.value ? "on" : ""}`} aria-pressed={type === t.value}
                  onClick={() => { setType(t.value); setLimit(20); }}>
            {t.label}{t.value && data?.by_type[t.value] ? ` (${data.by_type[t.value]})` : ""}
          </button>
        ))}
        <select className="input" style={{ width: "auto" }} value={level} aria-label="Xavf darajasi"
                onChange={(e) => setLevel(e.target.value as RiskLevel | "")}>
          <option value="">Barcha darajalar</option>
          <option value="high">▲▲ Yuqori</option>
          <option value="medium">▲ O'rta</option>
          <option value="low">● Past</option>
        </select>
      </div>
      {loading ? <Loading /> : error ? <ErrorBox message={error} onRetry={reload} /> :
        !data?.results.length ? <Empty title="Tavsiyalar yo'q" hint="Hozircha xavfli yoki tugayotgan tovar topilmadi." /> : (
          <>
            <span className="muted">{data.count} ta variant</span>
            {shown.map((item) => <InsightCard key={item.stock_id} item={item} canDiscount={isManager} />)}
            {data.results.length > limit && (
              <button className="btn btn-secondary" onClick={() => setLimit(limit + 20)}>Yana ko'rsatish</button>
            )}
          </>
        )}
    </div>
  );
}
