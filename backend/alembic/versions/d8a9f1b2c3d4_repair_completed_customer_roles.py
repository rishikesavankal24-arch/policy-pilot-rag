"""repair_completed_customer_roles

Revision ID: d8a9f1b2c3d4
Revises: ffcac183b342
Create Date: 2026-09-20 14:11:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a9f1b2c3d4'
down_revision: Union[str, Sequence[str], None] = 'ffcac183b342'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Repair existing completed customer roles."""
    op.execute(
        "UPDATE users SET role = 'CUSTOMER' "
        "WHERE requested_role = 'CUSTOMER' "
        "AND onboarding_status = 'COMPLETED' "
        "AND role = 'UNASSIGNED';"
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
