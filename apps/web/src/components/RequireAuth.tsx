import { useTranslation } from "react-i18next";
import { Navigate, Outlet } from "react-router";

import { useAuth } from "../auth/context";

/** Route guard: renders child routes only with a valid session. */
export function RequireAuth() {
  const { user, loading } = useAuth();
  const { t } = useTranslation();
  if (loading) return <p className="status">{t("common.loading")}</p>;
  if (user === null) return <Navigate to="/login" replace />;
  return <Outlet />;
}
