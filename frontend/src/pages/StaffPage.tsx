import { useState, type FormEvent } from "react";

import { api, ApiError } from "../api/client";
import type { Branch, Member, Page, Role } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorBox, Field, Loading, Success } from "../components/ui";
import { useAsync } from "../utils/useAsync";
import { Chips, toggle } from "./ProductFormPage";

const ROLES: Record<Role, string> = { owner: "Egasi", manager: "Menejer", cashier: "Sotuvchi" };

const blank = {
  phone: "", full_name: "", password: "", role: "cashier" as Role, branch_ids: [] as number[],
  can_approve_returns: false, is_active: true,
};

/** Yangi xodim qo'shish yoki mavjudini tahrirlash formasi (faqat do'kon egasi uchun). */
function MemberForm({ member, branches, onSaved, onCancel }: {
  member: Member | null; branches: Branch[]; onSaved: (msg: string) => void; onCancel: () => void;
}) {
  const [form, setForm] = useState(member ? { ...member, password: "" } : blank);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isOwnerRow = member?.role === "owner";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setFields({});
    try {
      if (member) {
        const body: Record<string, unknown> = { full_name: form.full_name, branch_ids: form.branch_ids };
        if (!isOwnerRow) {
          Object.assign(body, { role: form.role, is_active: form.is_active, can_approve_returns: form.can_approve_returns });
        }
        if (form.password) body.password = form.password;
        await api(`/auth/members/${member.id}/`, { method: "PATCH", body });
        onSaved("Xodim ma'lumotlari saqlandi.");
      } else {
        await api("/auth/members/", { method: "POST", body: form });
        onSaved("Xodim qo'shildi. U telefon raqami va parol bilan kira oladi.");
      }
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card stack" onSubmit={submit}>
      <h2 style={{ margin: 0 }}>{member ? `Tahrirlash: ${member.full_name || member.phone}` : "Yangi xodim"}</h2>
      {error && <ErrorBox message={error} />}
      <div className="grid-2">
        <Field label="Telefon *" error={fields.phone}>
          <input className="input" inputMode="tel" placeholder="+998 90 123 45 67" value={form.phone} disabled={!!member}
                 onChange={(e) => setForm({ ...form, phone: e.target.value })} required />
        </Field>
        <Field label="F.I.Sh." error={fields.full_name}>
          <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        </Field>
        <Field label={member ? "Yangi parol" : "Parol *"} error={fields.password}
               hint={member ? "Bo'sh qoldirilsa, parol o'zgarmaydi" : "Kamida 8 belgi"}>
          <input className="input" type="password" autoComplete="new-password" value={form.password}
                 onChange={(e) => setForm({ ...form, password: e.target.value })} required={!member} minLength={8} />
        </Field>
        {!isOwnerRow && (
          <Field label="Rol" error={fields.role}>
            <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
              <option value="cashier">Sotuvchi (kassa)</option>
              <option value="manager">Menejer</option>
            </select>
          </Field>
        )}
      </div>
      {form.role === "cashier" && (
        <Field label="Filiallar" error={fields.branch_ids} hint="Sotuvchi faqat tanlangan filiallarda ishlaydi">
          <Chips items={branches.filter((b) => b.is_active)} selected={form.branch_ids}
                 onToggle={(id) => setForm({ ...form, branch_ids: toggle(form.branch_ids, id) })} />
        </Field>
      )}
      {form.role === "cashier" && (
        <label className="row" style={{ gap: 8 }}>
          <input type="checkbox" checked={form.can_approve_returns}
                 onChange={(e) => setForm({ ...form, can_approve_returns: e.target.checked })} />
          Yaroqsiz tovar qaytarilishini tasdiqlay oladi (mas'ul shaxs)
        </label>
      )}
      {form.role !== "cashier" && <p className="muted" style={{ margin: 0 }}>Menejer barcha filiallarni ko'radi, tannarx va foydani ham ko'radi, qaytarishni tasdiqlaydi.</p>}
      {member && !isOwnerRow && (
        <label className="row" style={{ gap: 8 }}>
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Faol (o'chirilsa, xodim tizimga kira olmaydi)
        </label>
      )}
      <div className="row">
        <button type="button" className="btn btn-secondary" onClick={onCancel}>Bekor qilish</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saqlanmoqda..." : "Saqlash"}</button>
      </div>
    </form>
  );
}

export function StaffPage() {
  const { isOwner, me } = useAuth();
  const [editing, setEditing] = useState<Member | "new" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const data = useAsync(async () => {
    const [members, branches] = await Promise.all([
      api<Page<Member>>("/auth/members/?page_size=200"),
      api<Page<Branch>>("/auth/branches/?page_size=100"),
    ]);
    return { members: members.results, branches: branches.results };
  }, []);

  if (data.loading && !data.data) return <Loading />;
  if (data.error || !data.data) return <ErrorBox message={data.error ?? "Xatolik"} onRetry={data.reload} />;
  const { members, branches } = data.data;
  const branchName = (id: number) => branches.find((b) => b.id === id)?.name ?? `#${id}`;

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Xodimlar</h1>
        {isOwner && !editing && <button className="btn btn-primary" onClick={() => { setEditing("new"); setMessage(null); }}>+ Yangi xodim</button>}
      </div>
      {!isOwner && <div className="alert alert-warn">Xodimlarni faqat do'kon egasi qo'shadi va o'zgartiradi.</div>}
      {message && <Success>{message}</Success>}
      {editing && (
        <MemberForm key={editing === "new" ? "new" : editing.id} member={editing === "new" ? null : editing} branches={branches}
                    onCancel={() => setEditing(null)}
                    onSaved={(msg) => { setEditing(null); setMessage(msg); data.reload(); }} />
      )}
      <div className="card" style={{ padding: 0 }}>
        {!members.length ? <Empty title="Xodim yo'q" /> : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Xodim</th><th>Telefon</th><th>Rol</th><th>Filiallar</th><th>Holat</th><th /></tr></thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id}>
                    <td><b>{m.full_name || "—"}</b>{m.phone === me?.phone && <span className="muted"> (siz)</span>}</td>
                    <td className="num">{m.phone}</td>
                    <td>{ROLES[m.role]}{m.role === "cashier" && m.can_approve_returns && <div className="muted">Qaytarish uchun mas'ul</div>}</td>
                    <td>{m.role === "cashier" ? (m.branch_ids.map(branchName).join(", ") || <span className="field-error">Biriktirilmagan</span>) : "Barchasi"}</td>
                    <td>{m.is_active ? <span className="badge badge-ok">● Faol</span> : <span className="badge badge-neutral">○ O'chirilgan</span>}</td>
                    <td>{isOwner && <button className="btn btn-secondary btn-sm" onClick={() => { setEditing(m); setMessage(null); }}>✎ Tahrirlash</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
