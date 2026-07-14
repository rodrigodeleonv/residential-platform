import { Route, Routes } from "react-router";

import { AuthProvider } from "./auth/AuthProvider";
import { Layout } from "./components/Layout";
import { RequireAuth } from "./components/RequireAuth";
import { RequireRole } from "./components/RequireRole";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { UsersPage } from "./pages/UsersPage";

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route
              path="users"
              element={
                <RequireRole role="admin">
                  <UsersPage />
                </RequireRole>
              }
            />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  );
}
