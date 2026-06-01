"""add status and updated_at to qa_records

Revision ID: 20260531a1b2
Revises: None
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '20260531a1b2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 status 字段
    op.add_column('qa_records', sa.Column('status', sa.String(20), nullable=False, server_default='active'))
    op.create_index('ix_qa_records_status', 'qa_records', ['status'])

    # 添加 updated_at 字段
    op.add_column('qa_records', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))

    # 更新现有记录的 updated_at 为 created_at
    op.execute("UPDATE qa_records SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade() -> None:
    op.drop_index('ix_qa_records_status', table_name='qa_records')
    op.drop_column('qa_records', 'updated_at')
    op.drop_column('qa_records', 'status')
