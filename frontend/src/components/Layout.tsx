import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Logo } from "./Logo";

export const NAV = [
  { to: "/dashboard", label: "Bosh sahifa", icon: "🏠", managerOnly: false, mobile: true },
  { to: "/pos", label: "Kassa", icon: "🧾", managerOnly: false, mobile: true },
  { to: "/products", label: "Tovarlar", icon: "👕", managerOnly: false, mobile: true },
  { to: "/insights", label: "Aqlli tavsiyalar", icon: "💡", managerOnly: false, mobile: true },
  { to: "/stock", label: "Qoldiq", icon: "📦", managerOnly: false, mobile: false },
  { to: "/receipts", label: "Kirim", icon: "📥", managerOnly: false, mobile: false },
  { to: "/transfers", label: "Ko'chirish", icon: "🔁", managerOnly: false, mobile: false },
  { to: "/counts", label: "Inventarizatsiya", icon: "📋", managerOnly: false, mobile: false },
  { to: "/sales", label: "Savdolar", icon: "📈", managerOnly: false, mobile: false },
  { to: "/discounts", label: "Chegirmalar", icon: "🏷️", managerOnly: true, mobile: false },
  { to: "/reports", label: "Hisobotlar", icon: "📊", managerOnly: true, mobile: false },
  { to: "/settings", label: "Sozlamalar", icon: "⚙️", managerOnly: true, mobile: false },
];

export function Layout() {
  const { me, branch, setBranchId, logout, isManager } = useAuth();
  const branches = me?.branches ?? [];
  const items = NAV.filter((n) => !n.managerOnly || isManager);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand"><Logo /> Modiq</div>
        {items.map((n) => (
          <NavLink key={n.to} to={n.to} className="nav-link">
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
          <button className="btn btn-secondary btn-sm" onClick={logout}>Chiqish</button>
        </header>

        <main className="content">
          {branch ? <Outlet /> : (
            <div className="alert alert-warn">Sizga hech qaysi filial biriktirilmagan. Do'kon egasiga murojaat qiling.</div>
          )}
        </main>
      </div>

      <nav className="bottom-nav" aria-label="Asosiy menyu">
        {items.filter((n) => n.mobile).map((n) => (
          <NavLink key={n.to} to={n.to}>
            <span aria-hidden="true" style={{ fontSize: 20 }}>{n.icon}</span>
            {n.label === "Aqlli tavsiyalar" ? "Tavsiyalar" : n.label}
          </NavLink>
        ))}
        <NavLink to="/more"><span aria-hidden="true" style={{ fontSize: 20 }}>☰</span>Yana</NavLink>
      </nav>
    </div>
  );
}
