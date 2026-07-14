import { createContext, useContext } from "react";

import type { User } from "../api/types";

export interface AuthState {
  /** The signed-in user, or null when there is no valid session. */
  user: User | null;
  /** True until the initial session check finishes. */
  loading: boolean;
  /** Re-fetch the current user (after login). */
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const state = useContext(AuthContext);
  if (state === null) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return state;
}
