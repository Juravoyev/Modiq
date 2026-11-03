import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { RiskSettings } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorBox, Field, Loading, Success } from "../components/ui";
import { useAsync } from "../utils/useAsync";

function RiskSettingsCard() {
  const s = useAsync(() => api<RiskSettings>("/insights/settings/"), []);
  const [form, setForm] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { if (s.data) setForm(Object.fromEntries(Object.entries(s.data).map(([k, v]) => [k, String(v)]))); }, [s.data]);
  if (s.loading) return <Loading />;
  if (s.error) return <ErrorBox message={s.error} />;

  const items: { key: keyof RiskSettings; label: string; hint: string }[] = [
    { key: "no_sale_days", label: "Sotuvsiz kunlar chegarasi", hint: "Shuncha kun sotilmasa, sotilmay qolish xavfi" },
    { key: "sales_window_days", label: "Sotuv sur'ati davri (kun)", hint: "Sur'at oxirgi shuncha kun bo'yicha hisoblanadi" },
    { key: "min_sales_for_velocity", label: "Sur'at uchun minimal sotuv (dona)", hint: "Kamroq bo'lsa, sur'at ko'rsatilmaydi" },
    { key: "overstock_cover_days", label: "Ortiqcha zaxira chegarasi (kun)", hint: "Qoldiq shundan ko'p kunga yetsa, ortiqcha" },
    { key: "season_warning_days", label: "Mavsum oxiri ogohlantirishi (kun)", hint: "Mavsum tugashiga shuncha kun qolganda" },
  ];

  async function save() {
    setErr(null);
    setMsg(null);
    try {
      await api("/insights/settings/", { method: "PATCH", body: Object.fromEntries(Object.entries(form).map(([k, v]) => [k, Number(v)])) });
      setMsg("Xavf qoidalari saqlandi.");
    } catch (e) {
      const a = e as ApiError;
      setErr([a.message, ...Object.entries(a.fields ?? {}).map(([k, v]) => `${items.find((i) => i.key === k)?.label ?? k}: ${v}`)].join(" "));
    }
  }

  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>Xavf qoidalari</h2>
      <p className="muted" style={{ margin: 0 }}>Bu chegaralar "Aqlli tavsiyalar" sahifasidagi hisob-kitoblarda ishlatiladi. Har bir do'kon o'ziga mos qiymat tanlashi mumkin.</p>
      {msg && <Success>{msg}</Success>}
      {err && <ErrorBox message={err} />}
      <div className="grid-2">
        {items.map((i) => (
          <Field key={i.key} label={i.label} hint={i.hint}>
            <input className="input" inputMode="numeric" value={form[i.key] ?? ""} onChange={(e) => setForm({ ...form, [i.key]: e.target.value.replace(/\D/g, "") })} />
          </Field>
        ))}
      </div>
      <div><button className="btn btn-primary" onClick={save}>Saqlash</button></div>
    </div>
  );
}

export function SettingsPage() {
  const { me, isManager } = useAuth();
  if (!isManager) return <div className="alert alert-warn">Sozlamalar faqat menejer va do'kon egasi uchun.</div>;
  return (
    <div className="stack" style={{ maxWidth: 900 }}>
      <h1>Sozlamalar</h1>
      <div className="card">
        <h2>Do'kon</h2>
        <div className="facts"><span>Nomi: <b>{me?.business.name}</b></span><span>Valyuta: <b>{me?.business.currency}</b></span><span>Sana formati: <b>KK.OO.YYYY</b></span></div>
      </div>
      <div className="card spread">
        <span>Xodimlar va filiallar alohida sahifalarda boshqariladi.</span>
        <div className="row" style={{ gap: 8 }}>
          <Link className="btn btn-secondary btn-sm" to="/staff">👥 Xodimlar</Link>
          <Link className="btn btn-secondary btn-sm" to="/branches">🏬 Filiallar</Link>
        </div>
      </div>
      <RiskSettingsCard />
    </div>
  );
}
