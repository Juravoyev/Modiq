import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Logo } from "./Logo";

const NAV = [
  { to: "/", label: "Kassa", icon: "🧾", end: true },
  { to: "/products", label: "Tovarlar", icon: "👕" },
  { to: "/receipts", label: "Kirim", icon: "📥" },
  { to: "/stock", label: "Qoldiq", icon: "📦" },
  { to: "/sales", label: "Savdolar", icon: "📈" },
];

export function Layout() {
  const { me, branch, setBranchId, logout } = useAuth();
  const branches = me?.branches ?? [];

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand"><Logo /> Modiq</div>
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
            <span aria-hidden="true">{n.icon}</span> {n.label}
          </NavLink>
        ))}
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="row" style={{ gap: 8 }}>
            <span style={{ fontWeight: 700, color: "var(--green-dark)" }}>{me?.business.name}</span>
            {branches.length > 1 ? (
              <select
                className="input" style={{ width: "auto", minHeight: 36, padding: "4px 8px" }}
                value={branch?.id ?? ""} onChange={(e) => setBranchId(Number(e.target.value))}
                aria-label="Filial"
              >
                {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            ) : (
              <span className="muted">{branch?.name}</span>
            )}
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn btn-secondary btn-sm" onClick={logout}>Chiqish</button>
          </div>
        </header>

        <main className="content">
          {branch ? <Outlet /> : (
            <div className="alert alert-warn">Sizga hech qaysi filial biriktirilmagan. Do'kon egasiga murojaat qiling.</div>
          )}
        </main>
      </div>

      <nav className="bottom-nav" aria-label="Asosiy menyu">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end}>
            <span aria-hidden="true" style={{ fontSize: 20 }}>{n.icon}</span>
            {n.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
