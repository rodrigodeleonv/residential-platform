import type { ReactNode } from "react";
import { Navigate } from "react-router";

import type { Role } from "../api/types";
import { useAuth } from "../auth/context";

/** Route guard: renders children only when the user holds one of the roles. */
export function RequireRole({
  roles,
  children,
}: {
  roles: Role[];
  children: ReactNode;
}) {
  const { user } = useAuth();
  if (!user || !roles.some((role) => user.roles.includes(role))) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
