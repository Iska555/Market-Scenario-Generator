"""Append-only owner previews and public lifecycle; no automatic publication."""

import sqlalchemy as sa
from alembic import op

revision = "20261014_07"
down_revision = "20261014_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("publication_channels", sa.Column("id", sa.String(20), primary_key=True))
    op.execute("INSERT INTO publication_channels (id) VALUES ('demo')")
    op.create_table(
        "publication_previews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "portfolio_id",
            sa.Uuid(),
            sa.ForeignKey("portfolio_identities.portfolio_id"),
            nullable=False,
        ),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("head", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
    )
    op.create_table(
        "publication_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("sequence", sa.Integer(), nullable=False, unique=True),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("preview_id", sa.Uuid(), sa.ForeignKey("publication_previews.id")),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("action IN ('publish','withdraw')", name="ck_publication_action"),
    )
    if op.get_context().dialect.name == "postgresql":
        for table in ("publication_channels", "publication_previews", "publication_events"):
            op.execute(
                f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION guard_portfolio_identity()"
            )


def downgrade() -> None:
    for table in ("publication_events", "publication_previews", "publication_channels"):
        op.drop_table(table)
