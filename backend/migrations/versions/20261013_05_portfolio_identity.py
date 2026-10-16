"""Add birth-only portfolio identities without classifying historical records."""

import sqlalchemy as sa
from alembic import op

revision = "20261013_05"
down_revision = "20261011_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_identities",
        sa.Column(
            "portfolio_id", sa.Uuid(), sa.ForeignKey("accounting_portfolios.id"), primary_key=True
        ),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode IN ('demo','paper','real')", name="ck_portfolio_mode"),
    )
    if op.get_context().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION guard_portfolio_identity() RETURNS trigger AS $$
            BEGIN
                IF TG_OP <> 'INSERT' THEN
                    RAISE EXCEPTION 'Portfolio identities are append-only; no history relabelling';
                END IF;
                IF EXISTS (SELECT 1 FROM accounting_transactions
                           WHERE portfolio_id = NEW.portfolio_id) OR
                   NOT EXISTS (SELECT 1 FROM accounting_portfolios p
                               WHERE p.id = NEW.portfolio_id AND p.created_at = NEW.recorded_at
                                 AND EXISTS (SELECT 1 FROM pg_locks l
                                     WHERE l.locktype = 'transactionid'
                                       AND l.pid = pg_backend_pid() AND l.transactionid = p.xmin
                                       AND l.mode = 'ExclusiveLock' AND l.granted)) THEN
                    RAISE EXCEPTION 'Identity must be recorded at birth before ledger history';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql""")
        op.execute("""CREATE TRIGGER portfolio_identities_immutable
            BEFORE INSERT OR UPDATE OR DELETE
            ON portfolio_identities FOR EACH ROW EXECUTE FUNCTION guard_portfolio_identity()""")


def downgrade() -> None:
    op.drop_table("portfolio_identities")
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP FUNCTION guard_portfolio_identity()")
