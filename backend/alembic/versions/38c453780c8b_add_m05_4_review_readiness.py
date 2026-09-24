"""add_m05_4_review_readiness

Revision ID: 38c453780c8b
Revises: 4d7651d2aa49
Create Date: 2026-09-22 06:01:39.123510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38c453780c8b'
down_revision: Union[str, Sequence[str], None] = '4d7651d2aa49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for M05.4 Review Readiness."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('applications')]

    if 'review_readiness_status' not in columns:
        op.add_column(
            'applications',
            sa.Column(
                'review_readiness_status',
                sa.String(),
                nullable=False,
                server_default='PENDING_REVIEW_PREPARATION'
            )
        )
        op.create_index(
            op.f('ix_applications_review_readiness_status'),
            'applications',
            ['review_readiness_status'],
            unique=False
        )

    if 'review_readiness_updated_at' not in columns:
        op.add_column(
            'applications',
            sa.Column('review_readiness_updated_at', sa.DateTime(timezone=True), nullable=True)
        )

    if 'review_readiness_updated_by' not in columns:
        op.add_column(
            'applications',
            sa.Column('review_readiness_updated_by', sa.UUID(), nullable=True)
        )
        op.create_foreign_key(
            'fk_applications_readiness_updated_by_users',
            'applications',
            'users',
            ['review_readiness_updated_by'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    """Downgrade schema for M05.4 Review Readiness."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('applications')]
    fks = [fk['name'] for fk in inspector.get_foreign_keys('applications')]
    indexes = [ix['name'] for ix in inspector.get_indexes('applications')]

    if 'fk_applications_readiness_updated_by_users' in fks:
        op.drop_constraint('fk_applications_readiness_updated_by_users', 'applications', type_='foreignkey')

    if 'review_readiness_updated_by' in columns:
        op.drop_column('applications', 'review_readiness_updated_by')

    if 'review_readiness_updated_at' in columns:
        op.drop_column('applications', 'review_readiness_updated_at')

    if 'ix_applications_review_readiness_status' in indexes:
        op.drop_index(op.f('ix_applications_review_readiness_status'), table_name='applications')

    if 'review_readiness_status' in columns:
        op.drop_column('applications', 'review_readiness_status')
