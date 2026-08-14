from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()
