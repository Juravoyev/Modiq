import { useCallback, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Assistant } from "./Assistant";
import { Icon, type IconName } from "./Icon";
import { Logo } from "./Logo";

interface NavItem { to: string; label: string; icon: IconName; end?: boolean; managerOnly?: boolean; mobile?: boolean }

// mobile: telefonning pastki menyusida ko'rinadi, qolganlari "Yana" sahifasida.
export const NAV: NavItem[] = [
  { to: "/", label: "Kassa", icon: "cart", end: true, mobile: true },
  { to: "/dashboard", label: "Hisobot", icon: "chart", managerOnly: true },
  { to: "/insights", label: "Tavsiyalar", icon: "bulb", managerOnly: true },
  { to: "/products", label: "Tovarlar", icon: "shirt", mobile: true },
  { to: "/receipts", label: "Kirim", icon: "inbox", managerOnly: true },
  { to: "/transfers", label: "Ko'chirish", icon: "transfer", managerOnly: true },
  { to: "/stock", label: "Qoldiq", icon: "box", mobile: true },
  { to: "/sales", label: "Savdolar", icon: "receipt", mobile: true },
  { to: "/returns", label: "Qaytarish", icon: "undo" },
  { to: "/customers", label: "Mijozlar", icon: "user" },
  { to: "/promotions", label: "Aksiyalar", icon: "tag", managerOnly: true },
  { to: "/staff", label: "Xodimlar", icon: "users", managerOnly: true },
  { to: "/branches", label: "Filiallar", icon: "store", managerOnly: true },
];

export function navFor(isManager: boolean) {
  return NAV.filter((n) => isManager || !n.managerOnly);
}

export function Layout() {
  const { me, branch, setBranchId, logout, isManager } = useAuth();
  const branches = me?.branches ?? [];
  const nav = navFor(isManager);
  const [helpOpen, setHelpOpen] = useState(false);
  const closeHelp = useCallback(() => setHelpOpen(false), []);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand"><Logo /> Modiq</div>
        {nav.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
            <Icon name={n.icon} size={19} /> {n.label}
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
            <button className="btn btn-secondary btn-sm" onClick={() => setHelpOpen(true)} aria-haspopup="dialog">
              <Icon name="sparkles" size={16} /> Yordamchi
            </button>
            <button className="btn btn-secondary btn-sm" onClick={logout}><Icon name="logout" size={16} /> Chiqish</button>
          </div>
        </header>

        <main className="content">
          {branch ? <Outlet /> : (
            <div className="alert alert-warn">Sizga hech qaysi filial biriktirilmagan. Do'kon egasiga murojaat qiling.</div>
          )}
        </main>
      </div>

      <Assistant open={helpOpen} onClose={closeHelp} />

      <nav className="bottom-nav" aria-label="Asosiy menyu">
        {nav.filter((n) => n.mobile).map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end}>
            <Icon name={n.icon} size={22} />
            {n.label}
          </NavLink>
        ))}
        <NavLink to="/more">
          <Icon name="menu" size={22} />
          Yana
        </NavLink>
      </nav>
    </div>
  );
}
