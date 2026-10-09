"""Immutable portfolios and append-only accounting events."""

import sqlalchemy as sa
from alembic import op

revision = "20260912_03"
down_revision = "20260909_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_portfolios",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("broker", sa.String(200), nullable=False),
        sa.Column("account_label", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    decimal_type = sa.Numeric(30, 10).with_variant(sa.String(64), "sqlite")
    op.create_table(
        "accounting_transactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "portfolio_id", sa.Uuid(), sa.ForeignKey("accounting_portfolios.id"), nullable=False
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("security_id", sa.Uuid(), sa.ForeignKey("research_securities.id")),
        *[sa.Column(name, decimal_type) for name in ("quantity", "price", "amount")],
        sa.Column("fees", decimal_type, nullable=False),
        sa.Column("to_currency", sa.String(3)),
        *[sa.Column(name, decimal_type) for name in ("to_amount", "fx_rate")],
        sa.Column("reverses_id", sa.Uuid(), sa.ForeignKey("accounting_transactions.id")),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("external_reference", sa.String(200), nullable=False),
        sa.Column("note", sa.String(2000), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.UniqueConstraint("portfolio_id", "sequence", name="uq_ledger_sequence"),
        sa.UniqueConstraint(
            "portfolio_id", "source", "external_reference", name="uq_ledger_reference"
        ),
        sa.UniqueConstraint("reverses_id", name="uq_ledger_reversal"),
        sa.CheckConstraint("sequence > 0", name="ck_ledger_sequence"),
        sa.CheckConstraint(
            "type IN ('BUY','SELL','DIVIDEND','FEE','DEPOSIT','WITHDRAWAL',"
            "'FX_CONVERSION','REVERSAL')",
            name="ck_ledger_type",
        ),
    )
    op.create_index(
        "ix_ledger_replay",
        "accounting_transactions",
        ["portfolio_id", "effective_at", "recorded_at"],
    )
    if op.get_context().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION reject_ledger_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'Ledger records are append-only'; END;
            $$ LANGUAGE plpgsql""")
        for table in ("accounting_portfolios", "accounting_transactions"):
            op.execute(f"""CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation()""")


def downgrade() -> None:
    op.drop_table("accounting_transactions")
    op.drop_table("accounting_portfolios")
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_ledger_mutation()")
