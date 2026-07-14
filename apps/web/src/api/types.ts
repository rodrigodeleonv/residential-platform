export type Role = "admin" | "owner" | "tenant" | "guard";

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  roles: Role[];
}
