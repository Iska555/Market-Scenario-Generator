"""Append-only portfolio benchmark identity choices, without price archives."""

import sqlalchemy as sa
from alembic import op

revision = "20261011_04"
down_revision = "20260912_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_benchmark_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "portfolio_id", sa.Uuid(), sa.ForeignKey("accounting_portfolios.id"), nullable=False
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("identity", sa.JSON(none_as_null=True)),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.UniqueConstraint("portfolio_id", "revision", name="uq_benchmark_setting_revision"),
        sa.CheckConstraint("revision > 0", name="ck_benchmark_setting_revision"),
    )
    if op.get_context().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION reject_benchmark_setting_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'Benchmark settings are append-only'; END;
            $$ LANGUAGE plpgsql""")
        op.execute("""CREATE TRIGGER portfolio_benchmark_settings_immutable BEFORE UPDATE OR DELETE
            ON portfolio_benchmark_settings FOR EACH ROW
            EXECUTE FUNCTION reject_benchmark_setting_mutation()""")


def downgrade() -> None:
    op.drop_table("portfolio_benchmark_settings")
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_benchmark_setting_mutation()")
