import type { Sale } from "../api/types";
import { dateTime, money } from "../utils/format";

/** Savdo cheki (chop etish mumkin). */
export function Receipt({ sale, businessName }: { sale: Sale; businessName: string }) {
  return (
    <div className="receipt stack" style={{ gap: 8 }}>
      <div style={{ textAlign: "center" }}>
        <h2 style={{ marginBottom: 2 }}>{businessName}</h2>
        <div className="muted">{sale.branch_name}</div>
        <div className="muted">Chek № {sale.id} · {dateTime(sale.created_at)}</div>
        {sale.cashier_name && <div className="muted">Sotuvchi: {sale.cashier_name}</div>}
      </div>
      <div style={{ borderTop: "1px dashed var(--border)" }} />
      {sale.lines.map((l) => (
        <div key={l.id}>
          <div>{l.variant_name}</div>
          <div className="total-row num">
            <span className="muted">{l.quantity} × {money(l.unit_price)}{Number(l.discount_amount) > 0 && ` − ${money(l.discount_amount)}`}</span>
            <span>{money(l.line_total)}</span>
          </div>
        </div>
      ))}
      <div style={{ borderTop: "1px dashed var(--border)" }} />
      <div className="total-row num"><span>Summa</span><span>{money(sale.subtotal)}</span></div>
      {Number(sale.discount_total) > 0 && (
        <div className="total-row num"><span>Chegirma</span><span>−{money(sale.discount_total)}</span></div>
      )}
      <div className="total-row big num"><span>Jami</span><span>{money(sale.total)}</span></div>
      <div className="total-row"><span className="muted">To'lov turi</span><span>{sale.payment_type_display}</span></div>
      <div className="muted" style={{ textAlign: "center", marginTop: 8 }}>Xaridingiz uchun rahmat!</div>
    </div>
  );
}
