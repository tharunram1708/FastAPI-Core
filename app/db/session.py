from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import (
    DatabaseConstraintViolationError,
    DatabaseTransactionError,
)
from app.models.base import Base
from app.repositories.item_repository import ItemRepository
from app.repositories.enterprise_repository import EnterpriseRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.business_service import BusinessService
from app.services.item_service import ItemService


def _connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine: Engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args(settings.DATABASE_URL),
    pool_pre_ping=True,
)


if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class DatabaseSession:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.item_repository = ItemRepository(session)
        self.enterprise_repository = EnterpriseRepository(session)
        self.refresh_token_repository = RefreshTokenRepository(session)
        self.user_repository = UserRepository(session)
        self.items = ItemService(self.item_repository)
        self.business = BusinessService(self.enterprise_repository)
        self.enterprise = self.enterprise_repository
        self.auth = AuthService(
            self.user_repository,
            self.refresh_token_repository,
            self.enterprise_repository,
        )
        self.is_open = True
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.rollback()
            raise DatabaseConstraintViolationError() from exc
        except SQLAlchemyError as exc:
            self.rollback()
            raise DatabaseTransactionError() from exc
        else:
            self.committed = True

    def rollback(self) -> None:
        try:
            self.session.rollback()
        finally:
            self.rolled_back = True

    def close(self) -> None:
        self.session.close()
        self.is_open = False


@contextmanager
def managed_database_session() -> Generator[DatabaseSession]:
    database_session = DatabaseSession(SessionLocal())
    try:
        yield database_session
        database_session.commit()
    except DatabaseConstraintViolationError:
        database_session.rollback()
        raise
    except DatabaseTransactionError:
        database_session.rollback()
        raise
    except IntegrityError as exc:
        database_session.rollback()
        raise DatabaseConstraintViolationError() from exc
    except SQLAlchemyError as exc:
        database_session.rollback()
        raise DatabaseTransactionError() from exc
    except Exception:
        database_session.rollback()
        raise
    finally:
        database_session.close()


def get_database_session() -> Generator[DatabaseSession]:
    with managed_database_session() as database_session:
        yield database_session


def init_db() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
