import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/Logo";
import { ErrorBox, Field } from "../components/ui";

export function LoginPage() {
  const { me, login } = useAuth();
  const [phone, setPhone] = useState("+998 ");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (me) return <Navigate to="/" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(phone, password);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401
        ? "Telefon raqami yoki parol noto'g'ri."
        : (err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card stack" onSubmit={submit}>
        <div className="row" style={{ gap: 10 }}><Logo size={36} /><h1 style={{ margin: 0 }}>Modiq</h1></div>
        <p className="muted" style={{ margin: 0 }}>Do'koningiz hisobiga kiring</p>
        {error && <ErrorBox message={error} />}
        <Field label="Telefon raqami">
          <input className="input" type="tel" inputMode="tel" autoComplete="username" value={phone}
                 onChange={(e) => setPhone(e.target.value)} required />
        </Field>
        <Field label="Parol">
          <input className="input" type="password" autoComplete="current-password" value={password}
                 onChange={(e) => setPassword(e.target.value)} required />
        </Field>
        <button className="btn btn-primary btn-lg" disabled={busy}>{busy ? "Kirilmoqda..." : "Kirish"}</button>
        <p className="muted" style={{ textAlign: "center", margin: 0 }}>
          Hisobingiz yo'qmi? <Link to="/register">Do'konni ro'yxatdan o'tkazish</Link>
        </p>
      </form>
    </div>
  );
}
