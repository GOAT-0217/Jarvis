"""migrate admin role to super_admin

Revision ID: 002
Revises: 8b5e3e4d8e4b
Create Date: 2026-07-16 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, Sequence[str], None] = '8b5e3e4d8e4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate existing admin role to super_admin."""
    op.execute("UPDATE users SET role = 'super_admin' WHERE role = 'admin'")


def downgrade() -> None:
    """Revert super_admin back to admin."""
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'super_admin'")
