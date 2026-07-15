"""End-to-end test for the first-admin bootstrap script.

Runs the script in a subprocess on purpose: a fresh interpreter catches
regressions where the script's imports no longer resolve the full schema
(the API's own tests import every model module, masking that failure).
"""

import os
import secrets
import subprocess
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings

API_DIR = Path(__file__).parent.parent


def run_bootstrap(email: str, settings: Settings) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "python", "-m", "app.bootstrap", email, "First Admin"],
        cwd=API_DIR,
        env=os.environ | {"APP_DATABASE_URL": settings.database_url},
        capture_output=True,
        text=True,
    )


async def test_bootstrap_creates_first_admin(
    engine: AsyncEngine, settings: Settings
) -> None:
    email = f"first-admin-{secrets.token_hex(4)}@example.com"
    result = run_bootstrap(email, settings)
    try:
        assert result.returncode == 0, result.stderr
        async with engine.connect() as conn:
            role = await conn.scalar(
                text(
                    "SELECT ra.role FROM role_assignments ra"
                    " JOIN users u ON u.id = ra.user_id WHERE u.email = :email"
                ),
                {"email": email},
            )
        assert role == "admin"

        # Running it again must be a friendly no-op, not a crash.
        rerun = run_bootstrap(email, settings)
        assert rerun.returncode == 0, rerun.stderr
        assert "already exists" in rerun.stdout
    finally:
        # The script commits for real (no fixture rollback); clean up.
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM users WHERE email = :email"), {"email": email}
            )
