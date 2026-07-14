import type { ReactNode } from "react";
import { Navigate } from "react-router";

import type { Role } from "../api/types";
import { useAuth } from "../auth/context";

/** Route guard: renders children only when the user holds the role. */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user } = useAuth();
  if (!user?.roles.includes(role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}
