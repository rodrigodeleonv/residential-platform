import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/context";
import { LanguageToggle } from "./LanguageToggle";

export function Layout() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const isAdmin = user?.roles.includes("admin") ?? false;
  const isGuard = isAdmin || (user?.roles.includes("guard") ?? false);

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">{t("app.title")}</span>
        <nav>
          <NavLink to="/" end>
            {t("nav.home")}
          </NavLink>
          {isGuard && <NavLink to="/gatehouse">{t("nav.gatehouse")}</NavLink>}
          {isAdmin && <NavLink to="/users">{t("nav.users")}</NavLink>}
          {isAdmin && <NavLink to="/admin/units">{t("nav.units")}</NavLink>}
          {isAdmin && <NavLink to="/admin/billing">{t("nav.billing")}</NavLink>}
          {isAdmin && <NavLink to="/admin/areas">{t("nav.areas")}</NavLink>}
        </nav>
        <div className="actions">
          <LanguageToggle />
          <button type="button" className="ghost" onClick={() => void logout()}>
            {t("common.logout")}
          </button>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
