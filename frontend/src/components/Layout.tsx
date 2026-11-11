import { useCallback, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Assistant } from "./Assistant";
import { Icon, type IconName } from "./Icon";
import { Logo } from "./Logo";

type NavGroup = "Savdo" | "Ombor" | "Mijozlar" | "Boshqaruv";
interface NavItem { to: string; label: string; icon: IconName; group: NavGroup; end?: boolean; managerOnly?: boolean; mobile?: boolean }

// mobile: telefonning pastki menyusida ko'rinadi, qolganlari "Yana" sahifasida.
export const NAV: NavItem[] = [
  { to: "/", label: "Kassa", icon: "cart", group: "Savdo", end: true, mobile: true },
  { to: "/sales", label: "Savdolar", icon: "receipt", group: "Savdo", mobile: true },
  { to: "/returns", label: "Qaytarish", icon: "undo", group: "Savdo" },
  { to: "/products", label: "Tovarlar", icon: "shirt", group: "Ombor", mobile: true },
  { to: "/stock", label: "Qoldiq", icon: "box", group: "Ombor", mobile: true },
  { to: "/receipts", label: "Kirim", icon: "inbox", group: "Ombor", managerOnly: true },
  { to: "/transfers", label: "Ko'chirish", icon: "transfer", group: "Ombor", managerOnly: true },
  { to: "/customers", label: "Mijozlar", icon: "user", group: "Mijozlar" },
  { to: "/promotions", label: "Aksiyalar", icon: "tag", group: "Mijozlar", managerOnly: true },
  { to: "/dashboard", label: "Hisobot", icon: "chart", group: "Boshqaruv", managerOnly: true },
  { to: "/insights", label: "Tavsiyalar", icon: "bulb", group: "Boshqaruv", managerOnly: true },
  { to: "/staff", label: "Xodimlar", icon: "users", group: "Boshqaruv", managerOnly: true },
  { to: "/branches", label: "Filiallar", icon: "store", group: "Boshqaruv", managerOnly: true },
];
const GROUPS: NavGroup[] = ["Savdo", "Ombor", "Mijozlar", "Boshqaruv"];
const ROLE_LABEL = { owner: "Do'kon egasi", manager: "Menejer", cashier: "Sotuvchi" } as const;

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
        <nav className="sidebar-nav" aria-label="Bo'limlar">
          {GROUPS.map((g) => {
            const items = nav.filter((n) => n.group === g);
            if (!items.length) return null;
            return (
              <div key={g} className="nav-group">
                <div className="nav-group-title">{g}</div>
                {items.map((n) => (
                  <NavLink key={n.to} to={n.to} end={n.end} className="nav-link">
                    <Icon name={n.icon} size={19} /> {n.label}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </nav>
        {me && (
          <div className="sidebar-user">
            <span className="avatar" aria-hidden="true">{(me.full_name || me.phone).trim().charAt(0).toUpperCase()}</span>
            <span className="sidebar-user-text">
              <span className="sidebar-user-name">{me.full_name || me.phone}</span>
              <span className="sidebar-user-role">{ROLE_LABEL[me.role]}</span>
            </span>
          </div>
        )}
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-left">
            <span className="topbar-business">{me?.business.name}</span>
            {branches.length > 1 ? (
              <select
                className="input branch-select"
                value={branch?.id ?? ""} onChange={(e) => setBranchId(Number(e.target.value))}
                aria-label="Filial"
              >
                {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            ) : (
              <span className="muted">{branch?.name}</span>
            )}
          </div>
          <div className="topbar-actions">
            <button className="btn btn-secondary btn-sm" onClick={() => setHelpOpen(true)} aria-haspopup="dialog" aria-label="Yordamchi">
              <Icon name="sparkles" size={16} /> <span className="btn-label">Yordamchi</span>
            </button>
            <button className="btn btn-secondary btn-sm" onClick={logout} aria-label="Chiqish">
              <Icon name="logout" size={16} /> <span className="btn-label">Chiqish</span>
            </button>
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
