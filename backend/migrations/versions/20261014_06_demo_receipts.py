"""Immutable receipts for a deliberate isolated original demo load."""

import sqlalchemy as sa
from alembic import op

revision = "20261014_06"
down_revision = "20261013_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "demo_load_receipts",
        sa.Column(
            "portfolio_id",
            sa.Uuid(),
            sa.ForeignKey("portfolio_identities.portfolio_id"),
            primary_key=True,
        ),
        sa.Column("receipt", sa.JSON(), nullable=False),
    )
    if op.get_context().dialect.name == "postgresql":
        op.execute("""CREATE TRIGGER demo_load_receipts_immutable BEFORE UPDATE OR DELETE
            ON demo_load_receipts FOR EACH ROW EXECUTE FUNCTION guard_portfolio_identity()""")


def downgrade() -> None:
    op.drop_table("demo_load_receipts")
