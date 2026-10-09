"""Immutable thesis identities, content revisions and manual decision reviews."""

import sqlalchemy as sa
from alembic import op

revision = "20260909_02"
down_revision = "20260908_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_theses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "security_id", sa.Uuid(), sa.ForeignKey("research_securities.id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id", "security_id", name="uq_thesis_security"),
    )
    op.create_index("ix_thesis_security", "research_theses", ["security_id", "created_at"])
    op.create_table(
        "research_thesis_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thesis_id", sa.Uuid(), nullable=False),
        sa.Column("security_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ticker", sa.String(32), nullable=False),
        sa.Column("exchange", sa.String(32), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("horizon_months", sa.Integer(), nullable=False),
        sa.Column("conviction", sa.String(10), nullable=False),
        sa.Column("valuation_currency", sa.String(3), nullable=False),
        sa.Column("target_low", sa.Numeric(30, 10)),
        sa.Column("target_high", sa.Numeric(30, 10)),
        sa.Column("required_return", sa.Numeric(20, 10)),
        *[
            sa.Column(field, sa.String(10000), nullable=False)
            for field in (
                "variant_perception",
                "business_quality",
                "earnings_drivers",
                "catalysts",
                "risks",
                "bear_case",
                "base_case",
                "bull_case",
                "invalidation_conditions",
                "notes",
            )
        ],
        sa.ForeignKeyConstraint(
            ["thesis_id", "security_id"],
            ["research_theses.id", "research_theses.security_id"],
            name="fk_revision_thesis_security",
        ),
        sa.UniqueConstraint("thesis_id", "revision", name="uq_thesis_revision_number"),
        sa.UniqueConstraint("thesis_id", "id", name="uq_thesis_revision_identity"),
        sa.CheckConstraint("revision >= 1", name="ck_thesis_revision_number"),
        sa.CheckConstraint(
            "status IN ('draft','active','invalidated','closed')", name="ck_thesis_status"
        ),
        sa.CheckConstraint("conviction IN ('low','medium','high')", name="ck_thesis_conviction"),
        sa.CheckConstraint(
            "horizon_months > 0 AND horizon_months <= 1200", name="ck_thesis_horizon"
        ),
        sa.CheckConstraint(
            "(target_low IS NULL AND target_high IS NULL) OR "
            "(target_low IS NOT NULL AND target_high IS NOT NULL "
            "AND target_low > 0 AND target_high >= target_low)",
            name="ck_thesis_target_range",
        ),
        sa.CheckConstraint(
            "required_return IS NULL OR required_return > -1", name="ck_thesis_required_return"
        ),
    )
    op.create_index(
        "ix_thesis_revision_as_of", "research_thesis_revisions", ["thesis_id", "created_at"]
    )
    op.create_table(
        "research_thesis_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thesis_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", sa.String(10), nullable=False),
        sa.Column("current_price", sa.Numeric(30, 10)),
        sa.Column("valuation_currency", sa.String(3), nullable=False),
        *[
            sa.Column(field, sa.String(10000), nullable=False)
            for field in (
                "what_changed",
                "what_was_correct",
                "what_was_wrong",
                "new_information",
                "notes",
            )
        ],
        sa.Column("thesis_still_valid", sa.Boolean(), nullable=False),
        sa.Column("updated_expected_return", sa.Numeric(20, 10)),
        sa.ForeignKeyConstraint(
            ["thesis_id", "revision_id"],
            ["research_thesis_revisions.thesis_id", "research_thesis_revisions.id"],
            name="fk_review_thesis_revision",
        ),
        sa.CheckConstraint(
            "decision IN ('BUY_MORE','HOLD','REDUCE','EXIT','WATCH')",
            name="ck_thesis_review_decision",
        ),
        sa.CheckConstraint(
            "current_price IS NULL OR current_price > 0", name="ck_thesis_review_price"
        ),
        sa.CheckConstraint(
            "updated_expected_return IS NULL OR updated_expected_return > -1",
            name="ck_thesis_review_return",
        ),
    )
    op.create_index(
        "ix_thesis_review_history", "research_thesis_reviews", ["thesis_id", "reviewed_at"]
    )
    if op.get_context().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION reject_thesis_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'Thesis records are append-only'; END;
            $$ LANGUAGE plpgsql""")
        for table in ("research_theses", "research_thesis_revisions", "research_thesis_reviews"):
            op.execute(f"""CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE
                ON {table} FOR EACH ROW EXECUTE FUNCTION reject_thesis_mutation()""")


def downgrade() -> None:
    op.drop_table("research_thesis_reviews")
    op.drop_table("research_thesis_revisions")
    op.drop_table("research_theses")
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_thesis_mutation()")
