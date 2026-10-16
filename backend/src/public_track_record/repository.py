"""Birth-only classification, atomic with creation and independent of ledger versions."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from src.accounting.contracts import PortfolioCreate, PortfolioRead
from src.accounting.repository import LedgerRepository
from src.accounting.tables import Portfolio
from src.public_track_record.contracts import DemoCreate, PortfolioContext, PortfolioIdentity
from src.public_track_record.tables import PortfolioIdentityRow
from src.research.repository import ResearchConflict


def context(repository: LedgerRepository, portfolio: PortfolioRead) -> PortfolioContext:
    row = repository.session.get(PortfolioIdentityRow, portfolio.id)
    identity = PortfolioIdentity.model_validate(
        dict(
            mode=row.mode if row else "unclassified",
            recorded_at=row.recorded_at if row else None,
            publication_eligible=row is not None and row.mode == "demo",
        )
    )
    return PortfolioContext(**portfolio.model_dump(), identity=identity)


def portfolios(repository: LedgerRepository) -> list[PortfolioContext]:
    return [context(repository, portfolio) for portfolio in repository.portfolios()]


def create_demo(repository: LedgerRepository, data: DemoCreate) -> PortfolioContext:
    account = PortfolioCreate(
        id=data.id,
        name=data.name,
        base_currency=data.base_currency,
        broker="Synthetic demonstration",
        account_label="No real money invested",
    )
    existing = repository.session.get(Portfolio, data.id)
    if existing is not None:
        repository.portfolio(data.id)
        identity = repository.session.get(PortfolioIdentityRow, data.id)
        if identity is None or identity.mode != "demo":
            raise ResearchConflict("Existing history cannot be relabelled; create a separate demo")
        return context(repository, repository.create_portfolio(account))
    try:
        with repository.session.begin_nested():
            # Both inserts stay in the same live savepoint. PostgreSQL checks the
            # inserting transaction's lock, without comparing host/DB clocks.
            row = Portfolio(**account.model_dump(), created_at=datetime.now(UTC))
            repository.session.add(row)
            repository.session.flush()
            created = repository.read_portfolio(row)
            repository.session.add(
                PortfolioIdentityRow(
                    portfolio_id=created.id, mode=data.mode, recorded_at=created.created_at
                )
            )
            repository.session.flush()
    except IntegrityError as exc:
        raise ResearchConflict("Concurrent identity creation; retry the same demo ID") from exc
    return context(repository, created)
