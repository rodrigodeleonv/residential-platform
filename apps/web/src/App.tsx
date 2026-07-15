import { Route, Routes } from "react-router";

import { AuthProvider } from "./auth/AuthProvider";
import { Layout } from "./components/Layout";
import { RequireAuth } from "./components/RequireAuth";
import { RequireRole } from "./components/RequireRole";
import { AreasPage } from "./pages/admin/AreasPage";
import { BillingPage } from "./pages/admin/BillingPage";
import { UnitsAdminPage } from "./pages/admin/UnitsAdminPage";
import { GatehousePage } from "./pages/GatehousePage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { UnitPage } from "./pages/UnitPage";
import { UsersPage } from "./pages/UsersPage";

function admin(page: React.ReactNode) {
  return <RequireRole roles={["admin"]}>{page}</RequireRole>;
}

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="units/:unitId" element={<UnitPage />} />
            <Route
              path="gatehouse"
              element={
                <RequireRole roles={["guard", "admin"]}>
                  <GatehousePage />
                </RequireRole>
              }
            />
            <Route path="users" element={admin(<UsersPage />)} />
            <Route path="admin/units" element={admin(<UnitsAdminPage />)} />
            <Route path="admin/billing" element={admin(<BillingPage />)} />
            <Route path="admin/areas" element={admin(<AreasPage />)} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  );
}
