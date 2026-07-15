"""Import every module's models, registering the full schema on Base.

Cross-module foreign keys (e.g. role_assignments.unit_id -> units.id) only
resolve if the referenced module was imported. The API imports everything via
its routers; standalone entry points (migrations, scripts) import this module.
"""

# ruff: noqa: F401
import app.modules.audit.models
import app.modules.auth.models
import app.modules.billing.models
import app.modules.reservations.models
import app.modules.units.models
import app.modules.users.models
import app.modules.vehicles.models
import app.modules.visitors.models
