# Residential Platform — Development Plan

Source of truth for business rules: `requeriments.md` (Spanish, gitignored). This document translates those requirements into an implementation plan. When the two disagree, `requeriments.md` wins — flag the mismatch and update this plan.

Deployment-specific values (amenity catalog, time windows, capacities, retention periods) live only in the private requirements document; this plan deliberately keeps them generic.

## 1. Product summary

Management platform for a single condominium (not multi-tenant). Four user roles: **Admin** (the residential administrator, not a technical platform admin), **Owner** (legal owner of a unit, may or may not reside), **Tenant** (non-owner resident with time-boxed access), **Security guard** (gatehouse). One person can hold multiple roles (e.g. admin + resident). A few hundred users total.

Core modules: passwordless auth, units & occupancy, vehicles & parking, visitor management (gatehouse), common-area reservations, billing view (no payment processing yet), audit log.

## 2. Key business rules (settled)

- **Units**: either an apartment in a multi-floor building (building → floors → units) or an individual house. Each unit has a fixed number of assigned parking spots, but more vehicles than spots may be registered per unit. Separate pool of temporary visitor parking spots.
- **Occupancy**: a unit has 1+ legal owners (co-owners). A unit is occupied *either* by owners *or* by tenants, never both. Only responsible persons are registered (legal owners or tenants), not every family member.
- **Owner access**: permanent while ownership stands, regardless of residing or renting out.
- **Tenant access**: time-boxed by a contract date range set by the owner at registration. Registration by the owner *is* the authorization (no extra approval step). Access auto-deactivates at the end date; the owner can extend it. Any single co-owner can authorize/revoke tenants alone. Admins can also create/edit/revoke tenant registrations directly (support/disputes).
- **Privileges**: only owners see the unit's account statement/debts. Reservations, visitor pre-registration, and vehicle registration belong to whoever actually resides in the unit (owner-occupant or tenant); a non-resident owner cannot do these remotely.
- **Account creation (onboarding)**: admins create accounts (or send email invitations) for residents, other admins, and guards. Owners create accounts (or send email invitations) for their tenants.
- **Gatehouse**: guards see a restricted data subset (responsible resident name, contact phone, vehicle plate, building/house, unit number, assigned parking number). Two entry flows: (A) no pre-registration — guard phones the resident, who approves/denies live; (B) pre-registration — guard sees a valid pre-registration within its time window and lets the visitor in without a call.
- **Visitor pre-registration**: resident picks date, time, and one of a fixed set of expiration windows. The guard only sees the pre-registration within that window. Advance booking is capped, and pre-registrations can be one-off or recurring (by day/time/expiration) over a bounded range.
- **Visitor entry log**: entry AND exit are recorded, along with the assigned visitor parking spot (a physical marker with the spot number goes on the vehicle). Records are kept for a defined retention period.
- **Billing**: view-only. Pending debts (maintenance fee, common-area reservations, fines) and history of records manually marked as paid. Fines are issued by admins from a catalog of infraction types. No payment gateway integration for now; design so a provider abstraction can be added later.
- **Reservable areas**: a module where admins define areas with intrinsic attributes (e.g. parallel-booking capacity). Areas are condominium-wide (not per building/zone). The initial catalog and capacities come from the private requirements document.
- **Auth**: passwordless — email verification code and/or magic link.
- **Email**: provider-independent abstraction; initially a mock provider that prints to the console (no real email protocol).
- **i18n**: Spanish and English.
- **Audit log** — record changes produced by:
  - Login/logout
  - Resident updates (owner updates and tenant updates)
  - Creation/modification of visitor pre-registrations
  - Who authorized each visitor entry (guard)
  - Account changes made on *other* users' accounts (admin or any role acting on someone else)

## 3. Architecture decisions

Guiding constraint from requirements: avoid over-engineering, prefer simplicity, keep it modular.

- **Modular monolith**: one FastAPI app, code organized by domain module (`auth`, `users`, `units`, `vehicles`, `visitors`, `reservations`, `billing`, `audit`), not by technical layer across the whole app. Each module owns its routers, schemas, models, and service functions.
- **Layers inside a module**: router (HTTP) → service (business rules) → SQLAlchemy models. No repository pattern — at this scale SQLAlchemy sessions in services are enough.
- **Database**: PostgreSQL, SQLAlchemy 2.0 (async), Alembic for migrations.
- **AuthZ**: role-based with unit-scoped checks (e.g. "is current user a resident of unit X?"). Roles are assignments, not user types, since one person can be admin + owner + resident. Owner/tenant assignments carry a unit scope, and tenants also carry the contract date range. Occupancy is **derived, not stored**: a unit with an active tenancy is tenant-occupied, otherwise owner-occupied — this enforces the owners-XOR-tenants rule with no extra state, and tenancy expiry needs no background job (checked at authorization time).
- **Sessions**: httpOnly cookie sessions (server-side) rather than JWT — simpler and revocable, fine for a single first-party web app.
- **API versioning**: all backend endpoints live under the `/api/v0/` prefix. `v0` while the API is unstable/pre-release; bump to `v1`, `v2`, … only on breaking changes once stabilized.
- **Frontend**: Vite + React + TypeScript SPA in `apps/web`, talking to the API. react-i18next for ES/EN. Responsive layout (multi-device = responsive web; no native app planned).
- **Frontend testing**: Vitest + React Testing Library (unit), Playwright (e2e). Backend: pytest + httpx test client.
- **Deployment**: Docker Compose (api, web, postgres). Must run both in the cloud and locally/on-premises.
- **CI**: GitHub Actions (lint, typecheck, tests).

## 4. Development process

- Claude Code hooks run `ruff` + `pyright` automatically on edited Python files, and the equivalent linters/type checks on frontend files once `apps/web` exists.
- Every feature is completed together with tests that validate it (unit and/or integration; e2e for the critical flows).
- CI must stay green: lint + typecheck + tests on every push.

## 5. Phases

Each phase ends with working, tested, deployable software.

### Phase 0 — Foundations (mostly done)
- [x] Monorepo, git, `uv` project in `apps/api` with FastAPI, ruff, pyright
- [x] Claude Code hooks for Python (ruff + pyright) and frontend
- [x] Backend skeleton: app factory, settings (pydantic-settings), health endpoint
- [x] Docker Compose for local dev (api + postgres)
- [x] SQLAlchemy + Alembic wiring, first empty migration
- [x] pytest setup with a database fixture (test db + per-test transaction rollback)
- [ ] GitHub Actions CI (lint + typecheck + tests) — deferred until the GitHub repo is set up

### Phase 1 — Users, roles, passwordless auth (done)
- [x] User model, role assignments (admin / owner / tenant / guard)
- [x] Email OTP + magic-link login, cookie sessions, logout
- [x] Email abstraction with console/mock provider (real provider later, behind the same interface)
- [x] Onboarding: admin creates accounts or sends email invitations; first admin via `python -m app.bootstrap`
- [x] Audit hooks for login/logout and account changes on other users
- Owner creates/invites tenants: deferred to Phase 2 (needs units + ownership to scope the tenant role)

### Phase 2 — Physical structure & occupancy (done)
- [x] Buildings, floors, units, houses; visitor parking spots
- [x] Ownership (co-owners per unit) and tenancy (date-ranged; expiry enforced at authorization time)
- [x] Owner flows: register/extend/revoke tenant (any single co-owner); admin override flows; owner invites tenant accounts (the item deferred from Phase 1)
- [x] Enforce the owners-XOR-tenants occupancy rule (derived occupancy, see §3)
- [x] Audit: owner/tenant updates (owner_assigned/removed, tenant_registered/updated/revoked)

### Phase 3 — Vehicles & parking (done)
- [x] Fixed number of assigned parking spots per unit (limit configurable via settings), spot numbers unique condo-wide
- [x] Vehicle registry per unit: normalized unique plates; more vehicles than spots allowed
- [x] Resident-only registration enforced (a non-resident owner cannot register vehicles); unit members view, admin overrides

### Phase 4 — Frontend foundation
- Prerequisite: install Node.js LTS (nothing frontend-related is installed on the dev machine yet; npm ships with Node — deliberately deferred until this phase)
- Scaffold `apps/web` (Vite + React + TS), i18n ES/EN from day one
- Auth screens (email → code/link), session handling
- App shell with role-aware navigation (admin area vs resident area)
- Admin UI + resident UI for phases 1–3 features

### Phase 5 — Visitors & gatehouse (done)
- [x] Pre-registration by residents: one-off (start + expiration window) or recurring (weekday + time over a bounded range); policy limits (expiration options, advance cap, range cap) configurable via settings
- [x] Gatehouse for guards: restricted unit card (actual residents + phones, plates, spot numbers), active pre-registrations computed per window, flow A (resident approves live, validated as actual resident) and flow B (valid pre-registration)
- [x] Entry/exit log with visitor parking spot (marker) — spot busy while the visit is open; retention via settings + purge routine (cron/manual)
- [x] Audit: preregistration_created/updated/canceled, visitor_entry with who authorized

### Phase 6 — Common-area reservations
- Reservable-areas module: admin-managed catalog with intrinsic attributes (parallel-booking capacity)
- Seed the initial area catalog (names and capacities from the requirements doc)
- Resident booking flow with capacity-aware conflict prevention; cancellation

### Phase 7 — Billing (view-only)
- Charge records per unit: maintenance fees, reservation charges, fines
- Infraction catalog; admin issues fines from it
- Owner view: pending debts + paid history; admin marks records as paid
- Model money/concepts so a payment-provider abstraction can plug in later

### Phase 8 — Hardening & e2e
- Playwright e2e suites for the critical flows
- Security pass (authz review, rate limiting on auth endpoints)
- Production deployment setup (cloud + local)

## 6. Open questions

1. **Market comparison**: research commercial condominium-management / gatehouse platforms to identify key features worth adopting — pending, can run anytime.
2. **Reservation details** (Phase 6): booking time granularity (hourly? full-day?), cancellation policy, and whether any area has a cost — to be defined when the phase starts.
3. **Audit retention & visibility** (Phase 5+): scope is defined; still open — how long audit records are kept and who can view them (admins only?).
