import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Logo } from "./Logo";

interface NavItem { to: string; label: string; icon: string; end?: boolean; managerOnly?: boolean; mobile?: boolean }

// mobile: telefonning pastki menyusida ko'rinadi, qolganlari "Yana" sahifasida.
export const NAV: NavItem[] = [
  { to: "/", label: "Kassa", icon: "🧾", end: true, mobile: true },
  { to: "/products", label: "Tovarlar", icon: "👕", mobile: true },
  { to: "/receipts", label: "Kirim", icon: "📥", managerOnly: true },
  { to: "/transfers", label: "Ko'chirish", icon: "🔁", managerOnly: true },
  { to: "/stock", label: "Qoldiq", icon: "📦", mobile: true },
  { to: "/sales", label: "Savdolar", icon: "📈", mobile: true },
  { to: "/returns", label: "Qaytarish", icon: "↩" },
  { to: "/staff", label: "Xodimlar", icon: "👥", managerOnly: true },
  { to: "/branches", label: "Filiallar", icon: "🏬", managerOnly: true },
];

export function navFor(isManager: boolean) {
  return NAV.filter((n) => isManager || !n.managerOnly);
}

export function Layout() {
  const { me, branch, setBranchId, logout, isManager } = useAuth();
  const branches = me?.branches ?? [];
  const nav = navFor(isManager);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand"><Logo /> Modiq</div>
        {nav.map((n) => (
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
        {nav.filter((n) => n.mobile).map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end}>
            <span aria-hidden="true" style={{ fontSize: 20 }}>{n.icon}</span>
            {n.label}
          </NavLink>
        ))}
        <NavLink to="/more">
          <span aria-hidden="true" style={{ fontSize: 20 }}>☰</span>
          Yana
        </NavLink>
      </nav>
    </div>
  );
}
