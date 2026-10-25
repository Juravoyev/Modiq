import type { ReactNode } from "react";

export function Loading({ text = "Yuklanmoqda..." }: { text?: string }) {
  return (
    <div className="state" role="status">
      <div className="spinner" />
      {text}
    </div>
  );
}

export function Empty({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="state">
      <div style={{ fontSize: 28 }} aria-hidden="true">📦</div>
      <div style={{ fontWeight: 600, color: "var(--text)" }}>{title}</div>
      {hint && <div className="muted" style={{ marginTop: 4 }}>{hint}</div>}
      {action && <div style={{ marginTop: 12 }}>{action}</div>}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="alert alert-error" role="alert">
      <span aria-hidden="true">⚠</span>
      <div style={{ flex: 1 }}>{message}</div>
      {onRetry && <button className="btn btn-secondary btn-sm" onClick={onRetry}>Qayta urinish</button>}
    </div>
  );
}

export function Success({ children }: { children: ReactNode }) {
  return (
    <div className="alert alert-success" role="status">
      <span aria-hidden="true">✓</span>
      <div>{children}</div>
    </div>
  );
}

export function Field({ label, error, children, hint }: { label: string; error?: string; hint?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && !error && <span className="muted">{hint}</span>}
      {error && <span className="field-error" role="alert">{error}</span>}
    </label>
  );
}

export function Pagination({ page, count, pageSize = 25, onChange }: {
  page: number; count: number; pageSize?: number; onChange: (p: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="spread" style={{ marginTop: 12 }}>
      <span className="muted">Jami: {count}</span>
      <div className="row">
        <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>‹ Oldingi</button>
        <span className="muted">{page} / {pages}</span>
        <button className="btn btn-secondary btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>Keyingi ›</button>
      </div>
    </div>
  );
}

/** Qoldiq holati: rang + belgi + matn. */
export function StockBadge({ quantity, min }: { quantity: number; min: number }) {
  if (quantity <= 0) return <span className="badge badge-danger">✕ Tugagan</span>;
  if (quantity <= min) return <span className="badge badge-warn">▲ Kam qolgan</span>;
  return <span className="badge badge-ok">● Yetarli</span>;
}
