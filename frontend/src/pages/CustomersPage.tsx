import { useState, type FormEvent } from "react";

import { api, ApiError, qs } from "../api/client";
import type { BonusTransaction, Customer, CustomerGroup, Page } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorBox, Field, Loading, Pagination, Success } from "../components/ui";
import { dateTime, money } from "../utils/format";
import { useAsync, useDebounced } from "../utils/useAsync";
import { Icon } from "../components/Icon";

export function GroupBadge({ name, percent }: { name: string | null; percent: number }) {
  if (!name) return <span className="badge badge-neutral">Oddiy</span>;
  return <span className="badge badge-ok"><Icon name="star" size={12} /> {name} · {percent}%</span>;
}

/** Mijoz formasi. Kassada ham ishlatiladi (telefon oldindan to'ldirilgan holda). */
export function CustomerForm({ customer, groups, initialPhone = "", onSaved, onCancel }: {
  customer: Customer | null; groups: CustomerGroup[]; initialPhone?: string;
  onSaved: (c: Customer) => void; onCancel: () => void;
}) {
  const { isManager } = useAuth();
  const [form, setForm] = useState({
    phone: customer?.phone ?? initialPhone, full_name: customer?.full_name ?? "", note: customer?.note ?? "",
    group: customer?.group ? String(customer.group) : "",
  });
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    e.stopPropagation();
    setBusy(true);
    setError(null);
    setFields({});
    const body: Record<string, unknown> = { phone: form.phone, full_name: form.full_name, note: form.note };
    if (isManager) body.group = form.group ? Number(form.group) : null;
    try {
      const saved = await api<Customer>(customer ? `/customers/${customer.id}/` : "/customers/", {
        method: customer ? "PATCH" : "POST", body,
      });
      onSaved(saved);
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card stack" onSubmit={submit}>
      <h2>{customer ? `Tahrirlash: ${customer.full_name || customer.phone}` : "Yangi mijoz"}</h2>
      {error && <ErrorBox message={error} />}
      <div className="grid-2">
        <Field label="Telefon *" error={fields.phone}>
          <input className="input" inputMode="tel" value={form.phone} required placeholder="90 123 45 67"
                 onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </Field>
        <Field label="Ismi" error={fields.full_name}>
          <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        </Field>
        <Field label="Imtiyoz toifasi" error={fields.group}
               hint={isManager ? undefined : "Toifani egasi yoki menejer belgilaydi."}>
          <select className="input" value={form.group} disabled={!isManager}
                  onChange={(e) => setForm({ ...form, group: e.target.value })}>
            <option value="">Oddiy (imtiyozsiz)</option>
            {groups.map((g) => <option key={g.id} value={g.id}>{g.name} · {g.discount_percent}%</option>)}
          </select>
        </Field>
        <Field label="Izoh" error={fields.note}>
          <input className="input" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
        </Field>
      </div>
      <div className="row">
        <button type="button" className="btn btn-secondary" onClick={onCancel}>Bekor qilish</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saqlanmoqda..." : "Saqlash"}</button>
      </div>
    </form>
  );
}

function GroupsCard({ groups, onChanged }: { groups: CustomerGroup[]; onChanged: () => void }) {
  const [form, setForm] = useState({ name: "", discount_percent: "" });
  const [editing, setEditing] = useState<number | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setFields({});
    try {
      await api(editing ? `/customers/groups/${editing}/` : "/customers/groups/", {
        method: editing ? "PATCH" : "POST",
        body: { name: form.name, discount_percent: Number(form.discount_percent || 0) },
      });
      setForm({ name: "", discount_percent: "" });
      setEditing(null);
      onChanged();
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    }
  }

  async function remove(g: CustomerGroup) {
    if (!window.confirm(`"${g.name}" toifasini o'chirasizmi?`)) return;
    setError(null);
    try {
      await api(`/customers/groups/${g.id}/`, { method: "DELETE" });
      onChanged();
    } catch (err) {
      setError(g.customers_count > 0
        ? "Bu toifada mijozlar bor. Avval ularni boshqa toifaga o'tkazing."
        : (err as Error).message);
    }
  }

  return (
    <div className="card stack">
      <h2>Imtiyoz toifalari</h2>
      <p className="muted">
        Toifadagi mijozga kassada doimiy chegirma beriladi. Aksiya bilan ustma-ust qo'shilmaydi: ikkisidan mijoz
        uchun foydalirog'i olinadi. Narx tannarxdan pastga tushmaydi.
      </p>
      {error && <ErrorBox message={error} />}
      {groups.length > 0 && (
        <div className="stack gap-2">
          {groups.map((g) => (
            <div key={g.id} className="spread">
              <span><GroupBadge name={g.name} percent={g.discount_percent} /> <span className="muted">{g.customers_count} mijoz</span></span>
              <span className="row gap-2">
                <button className="btn btn-secondary btn-sm" onClick={() => {
                  setEditing(g.id); setForm({ name: g.name, discount_percent: String(g.discount_percent) });
                }} aria-label="Tahrirlash" title="Tahrirlash"><Icon name="pencil" size={15} /></button>
                <button className="btn btn-danger btn-sm" aria-label="O'chirish" title="O'chirish" onClick={() => remove(g)}><Icon name="trash" size={15} /></button>
              </span>
            </div>
          ))}
        </div>
      )}
      <form className="row" style={{ alignItems: "flex-end" }} onSubmit={submit}>
        <div style={{ flex: "2 1 180px" }}>
          <Field label="Toifa nomi" error={fields.name}>
            <input className="input" value={form.name} required placeholder="Masalan: VIP"
                   onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
        </div>
        <div style={{ flex: "1 1 100px" }}>
          <Field label="Chegirma, %" error={fields.discount_percent}>
            <input className="input" inputMode="numeric" value={form.discount_percent} required placeholder="0–50"
                   onChange={(e) => setForm({ ...form, discount_percent: e.target.value.replace(/[^\d]/g, "").slice(0, 2) })} />
          </Field>
        </div>
        <button className="btn btn-primary">{editing ? "Saqlash" : "+ Qo'shish"}</button>
        {editing && <button type="button" className="btn btn-secondary" onClick={() => { setEditing(null); setForm({ name: "", discount_percent: "" }); }}>Bekor</button>}
      </form>
    </div>
  );
}

function BonusHistory({ customer, onClose }: { customer: Customer; onClose: () => void }) {
  const rows = useAsync(() => api<BonusTransaction[]>(`/customers/${customer.id}/bonus/`), [customer.id]);
  const now = new Date();
  return (
    <div className="card stack">
      <div className="spread">
        <h2>Bonus tarixi: {customer.full_name || customer.phone}</h2>
        <button className="btn btn-secondary btn-sm" onClick={onClose}>Yopish</button>
      </div>
      <div className="row">
        <span>Ishlatish mumkin: <b className="num">{money(customer.bonus_available)}</b></span>
        {Number(customer.bonus_pending) > 0 && <span className="muted">Kutilmoqda: {money(customer.bonus_pending)}</span>}
      </div>
      {rows.loading ? <Loading /> : rows.error || !rows.data ? <ErrorBox message={rows.error ?? "Xatolik"} onRetry={rows.reload} /> :
        rows.data.length === 0 ? <p className="muted">Hali bonus harakati yo'q.</p> : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Sana</th><th>Harakat</th><th className="right">Summa</th></tr></thead>
              <tbody>
                {rows.data.map((t) => (
                  <tr key={t.id}>
                    <td className="num">{dateTime(t.created_at)}</td>
                    <td>
                      {t.kind_display}{t.sale && <span className="muted"> · chek № {t.sale}</span>}
                      {new Date(t.available_at) > now && <div className="muted">{dateTime(t.available_at)} dan ishlatiladi</div>}
                    </td>
                    <td className="right num" style={{ color: Number(t.amount) < 0 ? "var(--danger)" : "var(--green)" }}>
                      {Number(t.amount) > 0 ? "+" : ""}{money(t.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </div>
  );
}

export function CustomersPage() {
  const { isManager } = useAuth();
  const [query, setQuery] = useState("");
  const search = useDebounced(query.trim(), 300);
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Customer | "new" | null>(null);
  const [history, setHistory] = useState<Customer | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const groups = useAsync(() => api<CustomerGroup[]>("/customers/groups/"), []);
  const list = useAsync(() => api<Page<Customer>>(`/customers/${qs({ search, page })}`), [search, page]);

  return (
    <div className="stack">
      <div className="spread">
        <h1>Mijozlar</h1>
        {!editing && <button className="btn btn-primary" onClick={() => { setEditing("new"); setMessage(null); }}>+ Yangi mijoz</button>}
      </div>
      {message && <Success>{message}</Success>}
      {editing && (
        <CustomerForm key={editing === "new" ? "new" : editing.id} customer={editing === "new" ? null : editing}
                      groups={groups.data ?? []} onCancel={() => setEditing(null)}
                      onSaved={() => { setEditing(null); setMessage("Mijoz saqlandi."); list.reload(); groups.reload(); }} />
      )}
      {history && <BonusHistory key={history.id} customer={history} onClose={() => setHistory(null)} />}
      <input className="input" type="search" placeholder="Ism yoki telefon raqami" value={query}
             onChange={(e) => { setQuery(e.target.value); setPage(1); }} aria-label="Mijoz qidirish" />

      {list.loading && !list.data ? <Loading /> : list.error || !list.data ? (
        <ErrorBox message={list.error ?? "Xatolik"} onRetry={list.reload} />
      ) : list.data.results.length === 0 ? (
        <Empty title="Mijoz topilmadi" hint="Mijozni shu yerda yoki kassada telefon raqami bilan qo'shing." />
      ) : (
        <div className="card flush">
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Mijoz</th><th>Toifa</th><th className="right">Xaridlar</th><th className="right">Bonus</th><th /></tr></thead>
              <tbody>
                {list.data.results.map((c) => (
                  <tr key={c.id}>
                    <td><b>{c.full_name || "—"}</b><div className="muted num">{c.phone}</div></td>
                    <td><GroupBadge name={c.group_name} percent={c.discount_percent} /></td>
                    <td className="right num">
                      <div>{money(c.total_spent)}</div>
                      <div className="muted">{c.purchases_count} ta xarid</div>
                    </td>
                    <td className="right num">
                      <button className="btn btn-secondary btn-sm" onClick={() => setHistory(c)} title="Bonus tarixi">
                        <Icon name="gift" size={15} /> {money(c.bonus_available)}
                      </button>
                      {Number(c.bonus_pending) > 0 && <div className="muted">+{money(c.bonus_pending)} kutilmoqda</div>}
                    </td>
                    <td><button className="btn btn-secondary btn-sm" onClick={() => { setEditing(c); setMessage(null); }} aria-label="Tahrirlash" title="Tahrirlash"><Icon name="pencil" size={15} /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {list.data && <Pagination page={page} count={list.data.count} onChange={setPage} />}

      {isManager && groups.data && <GroupsCard groups={groups.data} onChanged={() => { groups.reload(); list.reload(); }} />}
    </div>
  );
}
