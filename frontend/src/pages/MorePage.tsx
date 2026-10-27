import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { NAV } from "../components/Layout";

/** Mobil ekranda pastki menyuga sig'magan bo'limlar. */
export function MorePage() {
  const { isManager, logout, me } = useAuth();
  return (
    <div className="stack">
      <h1>Bo'limlar</h1>
      <div className="more-grid">
        {NAV.filter((n) => !n.managerOnly || isManager).map((n) => (
          <Link key={n.to} to={n.to} className="card"><span style={{ fontSize: 24 }} aria-hidden="true">{n.icon}</span>{n.label}</Link>
        ))}
      </div>
      <div className="card spread">
        <span className="muted">{me?.full_name || me?.phone}</span>
        <button className="btn btn-secondary" onClick={logout}>Chiqish</button>
      </div>
    </div>
  );
}
