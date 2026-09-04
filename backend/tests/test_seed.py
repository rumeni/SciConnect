from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalog.models import (
    Institution,
    InstitutionAnalysisResearcher,
    InstrumentType,
    Researcher,
)
from app.seed import is_empty, seed_catalog


def _count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_seeding_an_empty_catalog_populates_it(db: Session) -> None:
    assert is_empty(db)

    message = seed_catalog(db)

    assert message.startswith("Seed completed")
    assert _count(db, Institution) == 5
    assert _count(db, Researcher) == 7
    assert _count(db, InstitutionAnalysisResearcher) == 11


def test_seeding_twice_leaves_the_catalog_unchanged(db: Session) -> None:
    seed_catalog(db)
    before = _count(db, Institution)

    message = seed_catalog(db)

    assert message == "Seed skipped: the catalog already contains data."
    assert _count(db, Institution) == before


def test_a_catalog_holding_only_reference_data_is_not_reseeded(db: Session) -> None:
    """A partly populated database must be left alone rather than collide."""
    db.add(InstrumentType(name="Real-Time PCR System"))
    db.flush()

    assert not is_empty(db)
    assert seed_catalog(db).startswith("Seed skipped")
    assert _count(db, Institution) == 0
