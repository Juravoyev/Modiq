import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/Logo";
import { ErrorBox, Field } from "../components/ui";

export function RegisterPage() {
  const { me, register } = useAuth();
  const [form, setForm] = useState({ business_name: "", full_name: "", phone: "+998 ", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  if (me) return <Navigate to="/" replace />;

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setFields({});
    try {
      await register(form);
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError) setFields(err.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card stack" onSubmit={submit}>
        <div className="row" style={{ gap: 10 }}><Logo size={36} /><h1 style={{ margin: 0 }}>Ro'yxatdan o'tish</h1></div>
        {error && <ErrorBox message={error} />}
        <Field label="Do'kon nomi" error={fields.business_name}>
          <input className="input" value={form.business_name} onChange={set("business_name")} required />
        </Field>
        <Field label="Ismingiz" error={fields.full_name}>
          <input className="input" value={form.full_name} onChange={set("full_name")} autoComplete="name" />
        </Field>
        <Field label="Telefon raqami" error={fields.phone}>
          <input className={`input ${fields.phone ? "invalid" : ""}`} type="tel" inputMode="tel" value={form.phone}
                 onChange={set("phone")} autoComplete="username" required />
        </Field>
        <Field label="Parol" error={fields.password} hint="Kamida 8 belgi, faqat raqamlardan iborat bo'lmasin">
          <input className={`input ${fields.password ? "invalid" : ""}`} type="password" value={form.password}
                 onChange={set("password")} autoComplete="new-password" minLength={8} required />
        </Field>
        <button className="btn btn-primary btn-lg" disabled={busy}>{busy ? "Yaratilmoqda..." : "Do'konni yaratish"}</button>
        <p className="muted" style={{ textAlign: "center", margin: 0 }}>
          Hisobingiz bormi? <Link to="/login">Kirish</Link>
        </p>
      </form>
    </div>
  );
}
