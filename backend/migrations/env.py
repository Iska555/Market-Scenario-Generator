"""Explicit migration entry point; never runs during application startup."""

import os

from alembic import context
from sqlalchemy import create_engine, pool
from src.research.tables import Base

config = context.config
target_metadata = Base.metadata


def run_migrations() -> None:
    # Tests can supply an isolated connection without changing application config.
    supplied = config.attributes.get("connection")
    if supplied is not None:
        context.configure(connection=supplied, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("Set DATABASE_URL to a PostgreSQL psycopg URL before running migrations")
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = create_engine(url, poolclass=pool.NullPool)
        try:
            with engine.connect() as connection:
                context.configure(
                    connection=connection, target_metadata=target_metadata, compare_type=True
                )
                with context.begin_transaction():
                    context.run_migrations()
        finally:
            engine.dispose()


run_migrations()
