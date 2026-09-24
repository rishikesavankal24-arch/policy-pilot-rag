"""add_m07_document_metadata

Revision ID: cf3977018e2c
Revises: 38c453780c8b
Create Date: 2026-09-24 10:26:31.205679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf3977018e2c'
down_revision: Union[str, Sequence[str], None] = '38c453780c8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for M07 Document Metadata."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [c['name'] for c in inspector.get_columns('documents')]

    if 'original_filename' not in existing_columns:
        op.add_column('documents', sa.Column('original_filename', sa.String(), nullable=True))
    if 'file_size_bytes' not in existing_columns:
        op.add_column('documents', sa.Column('file_size_bytes', sa.Integer(), nullable=True))
    if 'mime_type' not in existing_columns:
        op.add_column('documents', sa.Column('mime_type', sa.String(), nullable=True))
    if 'file_hash' not in existing_columns:
        op.add_column('documents', sa.Column('file_hash', sa.String(), nullable=True))
    if 'page_count' not in existing_columns:
        op.add_column('documents', sa.Column('page_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema for M07 Document Metadata."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [c['name'] for c in inspector.get_columns('documents')]

    if 'page_count' in existing_columns:
        op.drop_column('documents', 'page_count')
    if 'file_hash' in existing_columns:
        op.drop_column('documents', 'file_hash')
    if 'mime_type' in existing_columns:
        op.drop_column('documents', 'mime_type')
    if 'file_size_bytes' in existing_columns:
        op.drop_column('documents', 'file_size_bytes')
    if 'original_filename' in existing_columns:
        op.drop_column('documents', 'original_filename')

