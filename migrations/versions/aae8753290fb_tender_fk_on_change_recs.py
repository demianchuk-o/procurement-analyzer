"""tender FK on change recs

Revision ID: aae8753290fb
Revises: 2186884eb32b
Create Date: 2025-04-27 20:32:34.718942

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aae8753290fb'
down_revision = '2186884eb32b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('award_changes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tender_id', sa.String(length=32), nullable=False))
        batch_op.create_foreign_key(None, 'tenders', ['tender_id'], ['id'])

    with op.batch_alter_table('bid_changes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tender_id', sa.String(length=32), nullable=False))
        batch_op.create_foreign_key(None, 'tenders', ['tender_id'], ['id'])

    with op.batch_alter_table('complaint_changes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tender_id', sa.String(length=32), nullable=False))
        batch_op.create_foreign_key(None, 'tenders', ['tender_id'], ['id'])

    with op.batch_alter_table('tender_document_changes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tender_id', sa.String(length=32), nullable=False))
        batch_op.create_foreign_key(None, 'tenders', ['tender_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('tender_document_changes', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('tender_id')

    with op.batch_alter_table('complaint_changes', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('tender_id')

    with op.batch_alter_table('bid_changes', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('tender_id')

    with op.batch_alter_table('award_changes', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('tender_id')

    # ### end Alembic commands ###
