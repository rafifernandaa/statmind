import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base

_engine = None
_SessionLocal = None


def _build_engine():
    env = os.getenv("ENV", "development")
    if env == "production":
        user = os.environ["DB_USER"]
        password = os.environ["DB_PASS"]
        db_name = os.environ["DB_NAME"]
        # Cloud SQL Unix socket path injected by --add-cloudsql-instances
        socket_dir = os.environ.get(
            "DB_SOCKET_DIR",
            f"/cloudsql/my-project-31-491314:us-central1:statmind-db"
        )
        url = (
            f"postgresql+pg8000://{user}:{password}@/{db_name}"
            f"?unix_sock={socket_dir}/.s.PGSQL.5432"
        )
        engine = create_engine(url, pool_pre_ping=True)
    else:
        url = "sqlite:///./statmind_dev.db"
        engine = create_engine(url, connect_args={"check_same_thread": False})

    Base.metadata.create_all(bind=engine)
    return engine


def get_engine():
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


@contextmanager
def get_db():
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
