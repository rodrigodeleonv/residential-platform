"""initial baseline

Revision ID: 1276f5f12b0b
Revises:
Create Date: 2026-07-09 22:09:00.197066

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "1276f5f12b0b"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
