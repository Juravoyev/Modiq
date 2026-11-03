import { useState, type FormEvent } from "react";

import { api, ApiError } from "../api/client";
import type { Branch, Page } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorBox, Field, Loading, Success } from "../components/ui";
import { useAsync } from "../utils/useAsync";

const KINDS: Record<Branch["kind"], string> = { store: "Do'kon", warehouse: "Ombor" };

const blank: Omit<Branch, "id"> = { name: "", kind: "store", address: "", is_active: true };

function BranchForm({ branch, onSaved, onCancel }: { branch: Branch | null; onSaved: (msg: string) => void; onCancel: () => void }) {
  const [form, setForm] = useState<Omit<Branch, "id">>(branch ?? blank);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setFields({});
    try {
      await api(branch ? `/auth/branches/${branch.id}/` : "/auth/branches/", { method: branch ? "PATCH" : "POST", body: form });
      onSaved(branch ? "Filial saqlandi." : "Filial qo'shildi.");
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card stack" onSubmit={submit}>
      <h2 style={{ margin: 0 }}>{branch ? `Tahrirlash: ${branch.name}` : "Yangi filial"}</h2>
      {error && <ErrorBox message={error} />}
      <div className="grid-2">
        <Field label="Nomi *" error={fields.name}>
          <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </Field>
        <Field label="Turi" error={fields.kind}>
          <select className="input" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as Branch["kind"] })}>
            <option value="store">Do'kon (savdo qilinadi)</option>
            <option value="warehouse">Ombor</option>
          </select>
        </Field>
        <Field label="Manzil" error={fields.address}>
          <input className="input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        </Field>
      </div>
      {branch && (
        <label className="row" style={{ gap: 8 }}>
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Faol (yopilgan filial kassada va ro'yxatlarda ko'rinmaydi, tarixi saqlanadi)
        </label>
      )}
      {fields.is_active && <span className="field-error">{fields.is_active}</span>}
      <div className="row">
        <button type="button" className="btn btn-secondary" onClick={onCancel}>Bekor qilish</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saqlanmoqda..." : "Saqlash"}</button>
      </div>
    </form>
  );
}

export function BranchesPage() {
  const { reloadMe } = useAuth();
  const [editing, setEditing] = useState<Branch | "new" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const list = useAsync(() => api<Page<Branch>>("/auth/branches/?page_size=100").then((p) => p.results), []);

  if (list.loading && !list.data) return <Loading />;
  if (list.error || !list.data) return <ErrorBox message={list.error ?? "Xatolik"} onRetry={list.reload} />;

  return (
    <div className="stack">
      <div className="spread">
        <h1 style={{ margin: 0 }}>Filiallar</h1>
        {!editing && <button className="btn btn-primary" onClick={() => { setEditing("new"); setMessage(null); }}>+ Yangi filial</button>}
      </div>
      {message && <Success>{message}</Success>}
      {editing && (
        <BranchForm key={editing === "new" ? "new" : editing.id} branch={editing === "new" ? null : editing}
                    onCancel={() => setEditing(null)}
                    onSaved={(msg) => {
                      setEditing(null);
                      setMessage(msg);
                      list.reload();
                      // Yuqoridagi filial tanlovi ham yangilanishi kerak.
                      void reloadMe();
                    }} />
      )}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Nomi</th><th>Turi</th><th>Manzil</th><th>Holat</th><th /></tr></thead>
            <tbody>
              {list.data.map((b) => (
                <tr key={b.id} style={b.is_active ? undefined : { opacity: 0.6 }}>
                  <td><b>{b.name}</b></td>
                  <td>{KINDS[b.kind]}</td>
                  <td>{b.address || "—"}</td>
                  <td>{b.is_active ? <span className="badge badge-ok">● Faol</span> : <span className="badge badge-neutral">○ Yopilgan</span>}</td>
                  <td><button className="btn btn-secondary btn-sm" onClick={() => { setEditing(b); setMessage(null); }}>✎ Tahrirlash</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
