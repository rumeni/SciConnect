from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalog.models import (
    Institution,
    InstitutionAnalysisResearcher,
    InstrumentType,
    Researcher,
)
from app.seed import INSTITUTIONS, is_empty, reset_catalog, seed_catalog

EXPECTED_RESEARCHERS = sum(len(spec["researchers"]) for spec in INSTITUTIONS)
EXPECTED_ROLES = sum(
    len(offering.get("researchers", {}))
    for spec in INSTITUTIONS
    for offering in spec["offerings"]
)


def _count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_seeding_an_empty_catalog_populates_it(db: Session) -> None:
    assert is_empty(db)

    message = seed_catalog(db)

    assert message.startswith("Seed completed")
    assert _count(db, Institution) == len(INSTITUTIONS)
    assert _count(db, Researcher) == EXPECTED_RESEARCHERS
    assert _count(db, InstitutionAnalysisResearcher) == EXPECTED_ROLES


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


def test_reset_empties_the_catalogue(db: Session) -> None:
    seed_catalog(db)
    assert not is_empty(db)

    removed = reset_catalog(db)

    assert removed > 0
    assert is_empty(db)
    assert _count(db, InstitutionAnalysisResearcher) == 0
    assert _count(db, InstrumentType) == 0


def test_reset_then_seed_restores_the_same_catalogue(db: Session) -> None:
    """What `--reset` does: a second full load, not a doubled one."""
    seed_catalog(db)
    before = (_count(db, Institution), _count(db, Researcher))

    reset_catalog(db)
    message = seed_catalog(db)

    assert message.startswith("Seed completed")
    assert (_count(db, Institution), _count(db, Researcher)) == before


def test_reset_clears_hand_made_records_too(db: Session) -> None:
    db.add(InstrumentType(name="Something Added By Hand"))
    db.flush()

    reset_catalog(db)

    assert is_empty(db)
