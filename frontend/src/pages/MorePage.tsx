import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { navFor } from "../components/Layout";

/** Telefonda pastki menyuga sig'magan bo'limlar. */
export function MorePage() {
  const { isManager, me, logout } = useAuth();
  return (
    <div className="stack">
      <h1>Bo'limlar</h1>
      <div className="stack gap-2">
        {navFor(isManager).map((n) => (
          <Link key={n.to} to={n.to} className="result-item" style={{ textDecoration: "none", color: "inherit" }}>
            <span className="row gap-3"><Icon name={n.icon} size={20} /> {n.label}</span>
            <Icon name="chevron-right" className="muted" />
          </Link>
        ))}
      </div>
      <div className="muted">{me?.full_name || me?.phone}</div>
      <div><button className="btn btn-secondary" onClick={logout}>Chiqish</button></div>
    </div>
  );
}
