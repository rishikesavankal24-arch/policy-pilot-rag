"""add_m08_1_policy_tables

Revision ID: 438edf1ac68f
Revises: cf3977018e2c
Create Date: 2026-09-26 10:10:44.464550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '438edf1ac68f'
down_revision: Union[str, Sequence[str], None] = 'cf3977018e2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for M08.1 Policy and Regulatory Management foundation."""
    # 1. Create regulatory_authorities table
    op.create_table(
        'regulatory_authorities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('short_name', sa.String(), nullable=False),
        sa.Column('authority_type', sa.String(), server_default='CENTRAL_BANK', nullable=False),
        sa.Column('jurisdiction', sa.String(), nullable=True),
        sa.Column('website_url', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_regulatory_authorities_short_name'), 'regulatory_authorities', ['short_name'], unique=True)

    # 2. Create policies table (status column sa.Enum automatically creates policystatus ENUM in postgres)
    op.create_table(
        'policies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('policy_code', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('policy_type', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', 'ACTIVE', 'SUPERSEDED', 'ARCHIVED', name='policystatus'), nullable=False),
        sa.Column('institution', sa.String(), nullable=True),
        sa.Column('jurisdiction', sa.String(), nullable=True),
        sa.Column('current_version_id', sa.UUID(), nullable=True),
        sa.Column('regulatory_authority_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['regulatory_authority_id'], ['regulatory_authorities.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policies_policy_code'), 'policies', ['policy_code'], unique=True)
    op.create_index(op.f('ix_policies_status'), 'policies', ['status'], unique=False)
    op.create_index(op.f('ix_policies_current_version_id'), 'policies', ['current_version_id'], unique=False)
    op.create_index(op.f('ix_policies_regulatory_authority_id'), 'policies', ['regulatory_authority_id'], unique=False)

    # 3. Create policy_versions table
    op.create_table(
        'policy_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('policy_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.String(), nullable=False),
        sa.Column('changelog', sa.String(), nullable=True),
        sa.Column('file_url', sa.String(), nullable=True),
        sa.Column('file_hash', sa.String(), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('published_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['published_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'version_number', name='uq_policy_versions_policy_id_version_number')
    )
    op.create_index(op.f('ix_policy_versions_policy_id'), 'policy_versions', ['policy_id'], unique=False)
    op.create_index(op.f('ix_policy_versions_version_number'), 'policy_versions', ['version_number'], unique=False)
    op.create_index(op.f('ix_policy_versions_effective_from'), 'policy_versions', ['effective_from'], unique=False)
    op.create_index(op.f('ix_policy_versions_effective_to'), 'policy_versions', ['effective_to'], unique=False)
    op.create_index(op.f('ix_policy_versions_file_hash'), 'policy_versions', ['file_hash'], unique=False)

    # 4. Add circular foreign key for policies.current_version_id -> policy_versions.id
    op.create_foreign_key(
        'fk_policies_current_version_id',
        'policies',
        'policy_versions',
        ['current_version_id'],
        ['id'],
        ondelete='SET NULL',
        use_alter=True
    )

    # 5. Create policy_applicability table
    op.create_table(
        'policy_applicability',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('policy_id', sa.UUID(), nullable=False),
        sa.Column('institution', sa.String(), nullable=True),
        sa.Column('jurisdiction', sa.String(), nullable=True),
        sa.Column('loan_type', sa.String(), nullable=True),
        sa.Column('department', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policy_applicability_policy_id'), 'policy_applicability', ['policy_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema for M08.1 Policy and Regulatory Management foundation."""
    # 1. Drop foreign key constraint on policies.current_version_id
    op.drop_constraint('fk_policies_current_version_id', 'policies', type_='foreignkey')

    # 2. Drop policy_applicability
    op.drop_index(op.f('ix_policy_applicability_policy_id'), table_name='policy_applicability')
    op.drop_table('policy_applicability')

    # 3. Drop policy_versions
    op.drop_index(op.f('ix_policy_versions_file_hash'), table_name='policy_versions')
    op.drop_index(op.f('ix_policy_versions_effective_to'), table_name='policy_versions')
    op.drop_index(op.f('ix_policy_versions_effective_from'), table_name='policy_versions')
    op.drop_index(op.f('ix_policy_versions_version_number'), table_name='policy_versions')
    op.drop_index(op.f('ix_policy_versions_policy_id'), table_name='policy_versions')
    op.drop_table('policy_versions')

    # 4. Drop policies
    op.drop_index(op.f('ix_policies_regulatory_authority_id'), table_name='policies')
    op.drop_index(op.f('ix_policies_current_version_id'), table_name='policies')
    op.drop_index(op.f('ix_policies_status'), table_name='policies')
    op.drop_index(op.f('ix_policies_policy_code'), table_name='policies')
    op.drop_table('policies')

    # 5. Drop regulatory_authorities
    op.drop_index(op.f('ix_regulatory_authorities_short_name'), table_name='regulatory_authorities')
    op.drop_table('regulatory_authorities')

    # 6. Drop PolicyStatus enum
    op.execute("DROP TYPE IF EXISTS policystatus")
