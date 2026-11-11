import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AuthShell } from "../components/AuthShell";
import { ErrorBox, Field, PasswordInput } from "../components/ui";

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
    <AuthShell title="Xush kelibsiz" subtitle="Do'koningiz hisobiga kiring">
      <form className="stack" onSubmit={submit}>
        {error && <ErrorBox message={error} />}
        <Field label="Telefon raqami">
          <input className="input" type="tel" inputMode="tel" autoComplete="username" value={phone}
                 onChange={(e) => setPhone(e.target.value)} required />
        </Field>
        <Field label="Parol">
          <PasswordInput autoComplete="current-password" value={password}
                 onChange={(e) => setPassword(e.target.value)} required />
        </Field>
        <button className="btn btn-primary btn-lg" disabled={busy}>{busy ? "Kirilmoqda..." : "Kirish"}</button>
        <p className="muted center">
          Hisobingiz yo'qmi? <Link to="/register">Do'konni ro'yxatdan o'tkazish</Link>
        </p>
      </form>
    </AuthShell>
  );
}
