import { useEffect, useState } from "react";

import { api, ApiError } from "../api/client";
import type { Branch, Member, Page, RiskSettings, Role } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorBox, Field, Loading, Success } from "../components/ui";
import { useAsync } from "../utils/useAsync";

const ROLES: Record<Role, string> = { owner: "Egasi", manager: "Menejer", cashier: "Sotuvchi" };

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

function BranchesCard({ branches, reload }: { branches: Branch[]; reload: () => void }) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState<"store" | "warehouse">("store");
  const [err, setErr] = useState<string | null>(null);
  async function add() {
    setErr(null);
    try {
      await api("/auth/branches/", { method: "POST", body: { name, kind } });
      setName("");
      reload();
    } catch (e) {
      const a = e as ApiError;
      setErr(a.fields?.name || a.message);
    }
  }
  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>Filiallar va omborlar</h2>
      {branches.map((b) => (
        <div key={b.id} className="list-row"><span>{b.name}</span><span className="badge badge-neutral">{b.kind === "warehouse" ? "Ombor" : "Do'kon"}</span></div>
      ))}
      {err && <ErrorBox message={err} />}
      <div className="row" style={{ gap: 8 }}>
        <input className="input" style={{ flex: 1, minWidth: 160 }} placeholder="Yangi filial nomi" value={name} onChange={(e) => setName(e.target.value)} />
        <select className="input" style={{ width: "auto" }} value={kind} onChange={(e) => setKind(e.target.value as "store" | "warehouse")}>
          <option value="store">Do'kon</option><option value="warehouse">Ombor</option>
        </select>
        <button className="btn btn-secondary" disabled={!name.trim()} onClick={add}>Qo'shish</button>
      </div>
      <p className="muted" style={{ margin: 0 }}>Yangi filial ko'rinishi uchun sahifani yangilang (F5).</p>
    </div>
  );
}

function MemberRow({ m, branches, onSaved }: { m: Member; branches: Branch[]; onSaved: () => void }) {
  const [edit, setEdit] = useState(false);
  const [role, setRole] = useState<Role>(m.role);
  const [ids, setIds] = useState<number[]>(m.branch_ids);
  const [active, setActive] = useState(m.is_active);
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setErr(null);
    try {
      await api(`/auth/members/${m.id}/`, { method: "PATCH", body: { role, branch_ids: ids, is_active: active, ...(password ? { password } : {}) } });
      setEdit(false);
      onSaved();
    } catch (e) {
      const a = e as ApiError;
      setErr([a.message, ...Object.values(a.fields ?? {})].join(" "));
    }
  }

  if (!edit) {
    return (
      <div className="list-row">
        <span>
          <b>{m.full_name || m.phone}</b> {!m.is_active && <span className="badge badge-danger">✕ Bloklangan</span>}
          <div className="muted">{m.phone} · {ROLES[m.role]} · {m.branch_names.join(", ") || "filial biriktirilmagan"}</div>
        </span>
        {m.role !== "owner" && <button className="btn btn-secondary btn-sm" onClick={() => setEdit(true)}>Tahrirlash</button>}
      </div>
    );
  }
  return (
    <div className="stack" style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <b>{m.full_name || m.phone}</b>
      {err && <ErrorBox message={err} />}
      <div className="grid-2">
        <Field label="Rol">
          <select className="input" value={role} onChange={(e) => setRole(e.target.value as Role)}>
            <option value="cashier">Sotuvchi</option><option value="manager">Menejer</option>
          </select>
        </Field>
        <Field label="Yangi parol (ixtiyoriy)"><input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
      </div>
      {role === "cashier" && (
        <div className="row" style={{ gap: 8 }}>
          {branches.map((b) => (
            <button type="button" key={b.id} className={`chip ${ids.includes(b.id) ? "on" : ""}`}
                    onClick={() => setIds(ids.includes(b.id) ? ids.filter((x) => x !== b.id) : [...ids, b.id])}>{b.name}</button>
          ))}
        </div>
      )}
      <label className="row" style={{ gap: 8 }}><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /> Faol (o'chirilsa tizimga kira olmaydi)</label>
      <div className="row"><button className="btn btn-secondary" onClick={() => setEdit(false)}>Bekor qilish</button><button className="btn btn-primary" onClick={save}>Saqlash</button></div>
    </div>
  );
}

function MembersCard({ branches }: { branches: Branch[] }) {
  const list = useAsync(() => api<Page<Member>>("/auth/members/?page_size=100"), []);
  const [form, setForm] = useState({ full_name: "", phone: "+998 ", password: "", role: "cashier" as Role });
  const [ids, setIds] = useState<number[]>([]);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  async function add() {
    setErr(null);
    setFields({});
    try {
      await api("/auth/members/", { method: "POST", body: { ...form, branch_ids: ids } });
      setForm({ full_name: "", phone: "+998 ", password: "", role: "cashier" });
      setIds([]);
      setAdding(false);
      list.reload();
    } catch (e) {
      const a = e as ApiError;
      setErr(a.message);
      setFields(a.fields);
    }
  }

  return (
    <div className="card stack">
      <div className="spread"><h2 style={{ margin: 0 }}>Xodimlar</h2>
        {!adding && <button className="btn btn-primary btn-sm" onClick={() => setAdding(true)}>+ Xodim qo'shish</button>}</div>
      {list.loading ? <Loading /> : list.error ? <ErrorBox message={list.error} /> :
        list.data?.results.map((m) => <MemberRow key={m.id} m={m} branches={branches} onSaved={list.reload} />)}
      {adding && (
        <div className="stack" style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
          {err && <ErrorBox message={err} />}
          <div className="grid-2">
            <Field label="Ismi" error={fields.full_name}><input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
            <Field label="Telefon" error={fields.phone}><input className="input" type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="Parol" error={fields.password} hint="Kamida 8 belgi"><input className="input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
            <Field label="Rol" error={fields.role}>
              <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
                <option value="cashier">Sotuvchi</option><option value="manager">Menejer</option>
              </select>
            </Field>
          </div>
          {form.role === "cashier" && (
            <>
              <span className="field-label">Ishlaydigan filiallari</span>
              <div className="row" style={{ gap: 8 }}>
                {branches.map((b) => (
                  <button type="button" key={b.id} className={`chip ${ids.includes(b.id) ? "on" : ""}`}
                          onClick={() => setIds(ids.includes(b.id) ? ids.filter((x) => x !== b.id) : [...ids, b.id])}>{b.name}</button>
                ))}
              </div>
            </>
          )}
          <div className="row"><button className="btn btn-secondary" onClick={() => setAdding(false)}>Bekor qilish</button><button className="btn btn-primary" onClick={add}>Qo'shish</button></div>
        </div>
      )}
    </div>
  );
}

export function SettingsPage() {
  const { me, isManager } = useAuth();
  const branches = useAsync(() => api<Page<Branch>>("/auth/branches/?page_size=100"), []);
  if (!isManager) return <div className="alert alert-warn">Sozlamalar faqat menejer va do'kon egasi uchun.</div>;
  return (
    <div className="stack" style={{ maxWidth: 900 }}>
      <h1>Sozlamalar</h1>
      <div className="card">
        <h2>Do'kon</h2>
        <div className="facts"><span>Nomi: <b>{me?.business.name}</b></span><span>Valyuta: <b>{me?.business.currency}</b></span><span>Sana formati: <b>KK.OO.YYYY</b></span></div>
      </div>
      {branches.data && <BranchesCard branches={branches.data.results} reload={branches.reload} />}
      {branches.data && <MembersCard branches={branches.data.results} />}
      <RiskSettingsCard />
    </div>
  );
}
