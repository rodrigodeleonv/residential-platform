import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/context";
import { LanguageToggle } from "./LanguageToggle";

export function Layout() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const isAdmin = user?.roles.includes("admin") ?? false;

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">{t("app.title")}</span>
        <nav>
          <NavLink to="/" end>
            {t("nav.home")}
          </NavLink>
          {isAdmin && <NavLink to="/users">{t("nav.users")}</NavLink>}
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
