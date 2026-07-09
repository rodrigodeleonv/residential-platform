# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository currently contains only `requeriments.md` (requirements doc, in Spanish) — no code has been written yet. There are no build, lint, or test commands to document. Update this file with actual commands and architecture once the project is scaffolded.

## What Residential Platform is

A SaaS platform for condominium/residential management (not multi-tenant — one deployment per condominium). Core stack decided in requeriments.md:

- Python 3.13+ with FastAPI (backend)
- React or Vue (frontend — not yet chosen)
- PostgreSQL (database)
- Docker (deployment)
- Pytest for backend tests; equivalent popular tool for JS/TS frontend tests

## Domain model

- **User types**: Administradores (platform control), Residentes (live in the condo, may or may not own their unit), Propietarios (unit owners, may rent to non-owner residents), Policias/Seguridad (gate security — grant/deny visitor entry, can view limited resident/visitor data, report to administration). A user can hold more than one role (e.g. an administrator who is also a resident).
- **Residence types**: Apartamento en Torre (unit inside a multi-floor tower building) or Casa individual (standalone house).
- **Parking**: assigned resident/owner parking spots (numbered), plus separate temporary visitor parking spots.
- **Owners vs. non-owner residents**: open design question in requeriments.md — owners are expected to have permanent access and more privileges; non-owner residents may need temporary access that the owner authorizes.

## Key functional requirements to keep in mind

- Auth is passwordless: email verification code or magic link (no passwords).
- Payments need a provider-abstraction layer — expected providers are a bank's own payment platform and a local card-payment processor; specifics are still unknown, so don't hard-code a single provider's API.
- Common-area reservations (meeting rooms, gym, pool, etc.).
- Gate security screen shows only a limited data subset: responsible resident's name, contact phone, vehicle plate, tower/house, unit number, assigned parking number.
- Audit logging is required for reasonable changes across the platform.
- Vehicle plate registry for residents.
- Multi-language and multi-device support are required.

## Non-functional guidance from requeriments.md

- Scale target is modest: ~400 users. Avoid over-engineering — prefer simplicity, but keep the design modular/maintainable since new features will be added over time.
- Not multi-tenant by design.
- The developer working on this is strong in Python/backend/containers/Linux and databases, but has very little frontend experience and no prior exposure to React/Vue/TS. Prefer explaining frontend concepts more thoroughly and keep frontend architecture choices simple.
