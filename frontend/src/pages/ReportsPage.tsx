import { useState } from "react";

import { api, downloadFile, qs } from "../api/client";
import type { Report, ReportColumn } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorBox, Field, Loading } from "../components/ui";
import { isoDate, money } from "../utils/format";
import { useAsync } from "../utils/useAsync";

type Name = "sales" | "products" | "stock" | "slow" | "seasonal";
type Group = "day" | "week" | "month";

const TABS: { value: Name; label: string; dated: boolean }[] = [
  { value: "sales", label: "Savdo", dated: true },
  { value: "products", label: "Eng ko'p sotilgan", dated: true },
  { value: "stock", label: "Qoldiq qiymati", dated: false },
  { value: "slow", label: "Kam sotiladigan", dated: false },
  { value: "seasonal", label: "Mavsumiy xavf", dated: false },
];

const GROUPS: { value: Group; label: string; days: number }[] = [
  { value: "day", label: "Kunlik", days: 30 },
  { value: "week", label: "Haftalik", days: 84 },
  { value: "month", label: "Oylik", days: 365 },
];

function cell(col: ReportColumn, value: string | number | undefined) {
  if (value === undefined || value === null || value === "") return "";
  if (col.kind === "money") return money(value);
  if (col.kind === "pct") return `${String(value).replace(".", ",")}%`;
  return String(value);
}

export function ReportsPage() {
  const { branch } = useAuth();
  const [name, setName] = useState<Name>("sales");
  const [group, setGroup] = useState<Group>("day");
  const [dateFrom, setDateFrom] = useState(isoDate(-29));
  const [dateTo, setDateTo] = useState(isoDate());
  const [csvError, setCsvError] = useState<string | null>(null);
  const tab = TABS.find((t) => t.value === name)!;

  const params = {
    branch: branch?.id,
    group: name === "sales" ? group : undefined,
    date_from: tab.dated ? dateFrom : undefined,
    date_to: tab.dated ? dateTo : undefined,
  };
  const report = useAsync(() => api<Report>(`/reports/${name}/${qs(params)}`), [name, group, dateFrom, dateTo, branch?.id]);

  function pickGroup(g: Group) {
    setGroup(g);
    setDateFrom(isoDate(-(GROUPS.find((x) => x.value === g)!.days - 1)));
    setDateTo(isoDate());
  }

  async function exportCsv() {
    setCsvError(null);
    try {
      await downloadFile(`/reports/${name}/${qs({ ...params, export: "csv" })}`, `modiq-${name}-${tab.dated ? dateTo : isoDate()}.csv`);
    } catch (e) {
      setCsvError((e as Error).message);
    }
  }

  const r = report.data;
  return (
    <div className="stack">
      <div className="spread no-print">
        <h1 style={{ margin: 0 }}>Hisobotlar · {branch?.name}</h1>
        <div className="row" style={{ gap: 6 }}>
          <button className="btn btn-secondary btn-sm" disabled={!r} onClick={exportCsv}>CSV yuklab olish</button>
          <button className="btn btn-secondary btn-sm" disabled={!r} onClick={() => window.print()}>Chop etish / PDF</button>
        </div>
      </div>
      <div className="row no-print" style={{ gap: 8 }}>
        {TABS.map((t) => (
          <button key={t.value} className={`chip ${name === t.value ? "on" : ""}`} aria-pressed={name === t.value}
                  onClick={() => setName(t.value)}>{t.label}</button>
        ))}
      </div>
      {tab.dated && (
        <div className="row no-print" style={{ gap: 8, alignItems: "flex-end" }}>
          {name === "sales" && (
            <Field label="Guruhlash">
              <select className="input" value={group} onChange={(e) => pickGroup(e.target.value as Group)}>
                {GROUPS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </Field>
          )}
          <Field label="Boshlanish">
            <input className="input" type="date" value={dateFrom} max={dateTo} onChange={(e) => setDateFrom(e.target.value)} />
          </Field>
          <Field label="Tugash">
            <input className="input" type="date" value={dateTo} min={dateFrom} onChange={(e) => setDateTo(e.target.value)} />
          </Field>
        </div>
      )}
      {csvError && <ErrorBox message={csvError} />}
      {report.loading ? <Loading /> : report.error ? <ErrorBox message={report.error} onRetry={report.reload} /> : r && (
        <div className="card stack">
          <div>
            <h2 style={{ margin: 0 }}>{r.title}</h2>
            <div className="muted">
              {branch?.name} · {r.date_from ? `${r.date_from} — ${r.date_to}` : `${r.date_to} holatiga`}
            </div>
          </div>
          {!r.rows.length ? <Empty title="Ma'lumot yo'q" hint="Tanlangan davrda bu hisobot uchun yozuv topilmadi." /> : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>{r.columns.map((c) => <th key={c.key} className={c.kind === "text" ? "" : "right"}>{c.label}</th>)}</tr>
                </thead>
                <tbody>
                  {r.rows.map((row, i) => (
                    <tr key={i}>
                      {r.columns.map((c) => (
                        <td key={c.key} className={c.kind !== "text" ? "right num" : c.key === "period" ? "nowrap" : ""}>{cell(c, row[c.key])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
                {Object.keys(r.totals ?? {}).length > 0 && (
                  <tfoot>
                    <tr style={{ fontWeight: 700 }}>
                      {r.columns.map((c) => <td key={c.key} className={c.kind === "text" ? "" : "right num"}>{cell(c, r.totals[c.key])}</td>)}
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          )}
          {r.formulas.length > 0 && (
            <details className="why" open>
              <summary>Qanday hisoblandi?</summary>
              <ul className="why-body" style={{ margin: 0, paddingLeft: 18 }}>
                {r.formulas.map((f) => <li key={f}>{f}</li>)}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
