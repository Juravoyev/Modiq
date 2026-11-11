import { useState, type FormEvent } from "react";

import { api } from "../api/client";
import type { Customer, CustomerBrief, CustomerGroup, Page } from "../api/types";
import { CustomerForm, GroupBadge } from "../pages/CustomersPage";
import { ErrorBox } from "./ui";
import { Icon } from "./Icon";

function brief(c: Customer): CustomerBrief {
  return { id: c.id, phone: c.phone, full_name: c.full_name, group_name: c.group_name, discount_percent: c.discount_percent };
}

/** Kassada mijozni telefon raqami bilan topish yoki yangisini qo'shish. */
export function CustomerPicker({ value, onChange }: { value: CustomerBrief | null; onChange: (c: CustomerBrief | null) => void }) {
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [creating, setCreating] = useState<CustomerGroup[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function find(e: FormEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!phone.trim()) return;
    setBusy(true);
    setError(null);
    setNotFound(false);
    try {
      const res = await api<Page<Customer>>(`/customers/?phone=${encodeURIComponent(phone.trim())}`);
      if (res.results.length) {
        onChange(brief(res.results[0]));
        setPhone("");
      } else {
        setNotFound(true);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function startCreate() {
    setError(null);
    try {
      setCreating(await api<CustomerGroup[]>("/customers/groups/"));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (value) {
    return (
      <div className="spread" style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "8px 10px" }}>
        <div>
          <div className="row" style={{ fontWeight: 600, gap: 6 }}><Icon name="user" size={16} /> {value.full_name || value.phone}</div>
          <div className="muted num">{value.phone} <GroupBadge name={value.group_name} percent={value.discount_percent} /></div>
        </div>
        <button className="btn btn-secondary btn-sm" aria-label="Mijozni olib tashlash" onClick={() => onChange(null)}><Icon name="x" size={15} /></button>
      </div>
    );
  }

  if (creating) {
    return (
      <CustomerForm customer={null} groups={creating} initialPhone={phone}
                    onCancel={() => setCreating(null)}
                    onSaved={(c) => { setCreating(null); setNotFound(false); setPhone(""); onChange(brief(c)); }} />
    );
  }

  return (
    <div className="stack" style={{ gap: 6 }}>
      <form className="row" style={{ gap: 6, flexWrap: "nowrap" }} onSubmit={find}>
        <input className="input" inputMode="tel" placeholder="Mijoz telefoni (ixtiyoriy)" value={phone}
               onChange={(e) => { setPhone(e.target.value); setNotFound(false); }} aria-label="Mijoz telefoni" />
        <button className="btn btn-secondary" disabled={busy || !phone.trim()}>Topish</button>
      </form>
      {error && <ErrorBox message={error} />}
      {notFound && (
        <div className="spread">
          <span className="muted">Bu raqamli mijoz yo'q.</span>
          <button className="btn btn-secondary btn-sm" onClick={startCreate}>+ Yangi mijoz</button>
        </div>
      )}
    </div>
  );
}
