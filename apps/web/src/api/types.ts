export type Role = "admin" | "owner" | "tenant" | "guard";

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  roles: Role[];
}

// --- units ---

export type UnitKind = "apartment" | "house";

export interface Unit {
  id: number;
  kind: UnitKind;
  building_id: number | null;
  floor: number | null;
  number: string;
}

export interface Building {
  id: number;
  name: string;
}

export interface VisitorParkingSpot {
  id: number;
  number: string;
}

export interface Tenancy {
  id: number;
  user: User;
  starts_on: string;
  ends_on: string;
}

// --- vehicles ---

export interface ParkingSpot {
  id: number;
  unit_id: number;
  number: string;
}

export interface Vehicle {
  id: number;
  unit_id: number;
  plate: string;
  description: string | null;
}

// --- visitors ---

export type PreRegKind = "one_off" | "recurring";

export interface PreRegistration {
  id: number;
  unit_id: number;
  created_by_id: number | null;
  visitor_name: string;
  visitor_plate: string | null;
  kind: PreRegKind;
  expiration_hours: number;
  starts_at: string | null;
  weekday: number | null; // 0 = Monday
  time_of_day: string | null;
  valid_from: string | null;
  valid_until: string | null;
}

export interface GatehouseResident {
  user_id: number;
  full_name: string;
  phone: string | null;
}

export interface GatehouseUnitSummary {
  unit_id: number;
  kind: UnitKind;
  number: string;
  building_name: string | null;
}

export interface GatehouseUnitCard extends GatehouseUnitSummary {
  residents: GatehouseResident[];
  plates: string[];
  parking_spot_numbers: string[];
}

export interface Visit {
  id: number;
  unit_id: number;
  visitor_name: string;
  visitor_plate: string | null;
  visitor_spot_id: number | null;
  guard_id: number | null;
  authorized_by_id: number | null;
  preregistration_id: number | null;
  entered_at: string;
  exited_at: string | null;
}

// --- reservations ---

export type TimeSlot = "morning" | "afternoon" | "evening";

export interface Area {
  id: number;
  name: string;
  description: string | null;
  capacity: number;
  fee: string; // Decimal serialized as string
  is_active: boolean;
  currency: string;
}

export interface SlotAvailability {
  slot: TimeSlot;
  capacity: number;
  booked: number;
  available: number;
}

export interface Reservation {
  id: number;
  area_id: number;
  unit_id: number;
  user_id: number;
  day: string;
  slot: TimeSlot;
  fee: string;
  canceled_at: string | null;
  currency: string;
}

// --- billing ---

export type ChargeKind = "maintenance" | "reservation" | "fine";

export interface Charge {
  id: number;
  unit_id: number;
  kind: ChargeKind;
  description: string;
  amount: string;
  reservation_id: number | null;
  infraction_type_id: number | null;
  paid_at: string | null;
  voided_at: string | null;
  created_at: string;
  currency: string;
}

export interface Statement {
  currency: string;
  pending: Charge[];
  pending_total: string;
  paid: Charge[];
}

export interface Infraction {
  id: number;
  name: string;
  description: string | null;
  fine_amount: string;
  is_active: boolean;
  currency: string;
}
