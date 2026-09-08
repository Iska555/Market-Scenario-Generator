"""Equity security master and immutable point-in-time fundamental observations."""

import sqlalchemy as sa
from alembic import op

revision = "20260908_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_securities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ticker", sa.String(32), nullable=False),
        sa.Column("exchange", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("sector", sa.String(200)),
        sa.Column("industry", sa.String(200)),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("isin", sa.String(12)),
        sa.Column("figi", sa.String(12)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("exchange", "ticker", name="uq_security_listing"),
        sa.CheckConstraint("asset_type = 'equity'", name="ck_security_equity"),
    )
    op.create_table(
        "research_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "security_id", sa.Uuid(), sa.ForeignKey("research_securities.id"), nullable=False
        ),
        sa.Column("metric", sa.String(200), nullable=False),
        sa.Column("value", sa.Numeric(30, 10), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3)),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_kind", sa.String(20), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("source_record_id", sa.String(200), nullable=False),
        sa.Column("source_document", sa.String(1000), nullable=False),
        sa.Column("basis", sa.String(200), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("version_sha256", sa.String(64), nullable=False),
        sa.UniqueConstraint("source", "source_record_id", name="uq_observation_source_record"),
        sa.UniqueConstraint("version_sha256", name="uq_observation_publication"),
        sa.CheckConstraint(
            "reported_at <= fetched_at AND fetched_at <= recorded_at",
            name="ck_observation_availability",
        ),
        sa.CheckConstraint(
            "period_start IS NULL OR period_start <= period_end", name="ck_observation_period"
        ),
        sa.CheckConstraint("unit IN ('currency','ratio','fraction')", name="ck_observation_unit"),
        sa.CheckConstraint(
            "period_kind IN ('instant','quarter','annual','ttm','estimate')",
            name="ck_observation_period_kind",
        ),
        sa.CheckConstraint(
            "(unit = 'currency' AND currency IS NOT NULL) OR "
            "(unit <> 'currency' AND currency IS NULL)",
            name="ck_observation_currency",
        ),
    )
    op.create_index(
        "ix_observation_as_of",
        "research_observations",
        ["security_id", "reported_at", "recorded_at"],
    )
    if op.get_context().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION reject_research_fact_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'Research observations are append-only'; END;
            $$ LANGUAGE plpgsql""")
        op.execute("""CREATE TRIGGER research_facts_immutable BEFORE UPDATE OR DELETE
            ON research_observations FOR EACH ROW
            EXECUTE FUNCTION reject_research_fact_mutation()""")


def downgrade() -> None:
    op.drop_table("research_observations")
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_research_fact_mutation()")
    op.drop_table("research_securities")
