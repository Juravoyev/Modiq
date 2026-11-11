import type { ReactNode } from "react";

import { Icon } from "./Icon";
import { Logo } from "./Logo";

const FEATURES = [
  "Kassa: shtrix-kod, chegirma va bonus bilan tez savdo",
  "Ombor: har bir rang va o'lcham bo'yicha aniq qoldiq",
  "Hisobot: kunlik tushum, foyda va sotilmayotgan tovarlar",
];

/** Kirish va ro'yxatdan o'tish sahifalari qobig'i: chapda brend paneli (telefonda yashirin), o'ngda forma. */
export function AuthShell({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="auth-page">
      <aside className="auth-brand">
        <div className="auth-brand-logo"><Logo size={40} /> Modiq</div>
        <div>
          <p className="auth-brand-title">Kiyim do'koningiz hisobi bir joyda</p>
          <ul className="auth-brand-list">
            {FEATURES.map((f) => <li key={f}><Icon name="check-circle" size={20} /> {f}</li>)}
          </ul>
        </div>
        <span className="auth-brand-foot">Kiyim, poyabzal va sumka do'konlari uchun</span>
      </aside>
      <main className="auth-main">
        <div className="auth-card stack">
          <div className="auth-mobile-logo"><Logo size={36} /> Modiq</div>
          <div>
            <h1>{title}</h1>
            {subtitle && <p className="muted mt-1">{subtitle}</p>}
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
