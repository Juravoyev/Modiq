import type { DocStatus, RiskLevel } from "../api/types";

const DOC: Record<DocStatus, { label: string; cls: string; icon: string }> = {
  draft: { label: "Qoralama", cls: "badge-neutral", icon: "○" },
  sent: { label: "Jo'natilgan", cls: "badge-warn", icon: "➜" },
  received: { label: "Qabul qilingan", cls: "badge-ok", icon: "✓" },
  confirmed: { label: "Tasdiqlangan", cls: "badge-ok", icon: "✓" },
  applied: { label: "Tasdiqlangan", cls: "badge-ok", icon: "✓" },
  cancelled: { label: "Bekor qilingan", cls: "badge-danger", icon: "✕" },
};

export function DocStatusBadge({ status }: { status: DocStatus }) {
  const s = DOC[status];
  return <span className={`badge ${s.cls}`}>{s.icon} {s.label}</span>;
}

const LEVEL: Record<RiskLevel, { label: string; cls: string; icon: string }> = {
  high: { label: "Yuqori xavf", cls: "badge-danger", icon: "▲▲" },
  medium: { label: "O'rta xavf", cls: "badge-warn", icon: "▲" },
  low: { label: "Past xavf", cls: "badge-neutral", icon: "●" },
};

/** Xavf darajasi: rang + belgi + matn. */
export function RiskBadge({ level }: { level: RiskLevel }) {
  const s = LEVEL[level];
  return <span className={`badge ${s.cls}`}><span aria-hidden="true">{s.icon}</span> {s.label}</span>;
}
