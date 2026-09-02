from sqlalchemy.orm import Session

from app.modules.catalog.models import (
    AnalysisType,
    Institution,
    InstitutionAnalysis,
    InstitutionAnalysisTarget,
    InstitutionInstrument,
    InstrumentType,
    Microorganism,
)
from app.modules.catalog.service import (
    CapabilityFilters,
    link_analysis_instrument,
    search_capabilities,
)


def _build_scenario(db: Session) -> dict[str, object]:
    pcr = InstrumentType(name="PCR System")
    microscope = InstrumentType(name="Microscope")
    analysis_type = AnalysisType(name="PCR analysis")
    organism = Microorganism(scientific_name="SARS-CoV-2")
    first = Institution(
        name="First Institute", slug="first", city="Belgrade", country="Serbia", status="active"
    )
    second = Institution(
        name="Second Institute", slug="second", city="Novi Sad", country="Serbia", status="active"
    )
    db.add_all([pcr, microscope, analysis_type, organism, first, second])
    db.flush()

    first_pcr = InstitutionInstrument(
        institution_id=first.id, instrument_type_id=pcr.id, status="operational"
    )
    second_pcr = InstitutionInstrument(
        institution_id=second.id, instrument_type_id=pcr.id, status="operational"
    )
    second_microscope = InstitutionInstrument(
        institution_id=second.id, instrument_type_id=microscope.id, status="operational"
    )
    db.add_all([first_pcr, second_pcr, second_microscope])
    db.flush()

    first_offering = InstitutionAnalysis(
        institution_id=first.id,
        analysis_type_id=analysis_type.id,
        availability="available",
    )
    second_offering = InstitutionAnalysis(
        institution_id=second.id,
        analysis_type_id=analysis_type.id,
        availability="available",
    )
    db.add_all([first_offering, second_offering])
    db.flush()
    link_analysis_instrument(
        db, institution_analysis=first_offering, institution_instrument=first_pcr
    )
    link_analysis_instrument(
        db, institution_analysis=second_offering, institution_instrument=second_microscope
    )
    db.add(
        InstitutionAnalysisTarget(
            institution_analysis_id=first_offering.id, microorganism_id=organism.id
        )
    )
    db.commit()
    return {
        "pcr": pcr,
        "analysis": analysis_type,
        "organism": organism,
        "first": first,
        "second": second,
        "first_offering": first_offering,
        "second_pcr": second_pcr,
    }


def test_instrument_only_finds_every_institution_that_owns_it(db: Session) -> None:
    data = _build_scenario(db)
    result = search_capabilities(
        db, CapabilityFilters(instrument_type_ids=[data["pcr"].id])
    )
    assert {item.institution.name for item in result.items} == {
        "First Institute",
        "Second Institute",
    }
    second = next(item for item in result.items if item.institution.name == "Second Institute")
    assert second.matched_analyses == []


def test_analysis_and_instrument_require_a_direct_offering_link(db: Session) -> None:
    data = _build_scenario(db)
    result = search_capabilities(
        db,
        CapabilityFilters(
            analysis_type_ids=[data["analysis"].id],
            instrument_type_ids=[data["pcr"].id],
        ),
    )
    assert [item.institution.name for item in result.items] == ["First Institute"]


def test_analysis_microorganism_and_instrument_are_matched_on_same_offering(
    db: Session,
) -> None:
    data = _build_scenario(db)
    result = search_capabilities(
        db,
        CapabilityFilters(
            analysis_type_ids=[data["analysis"].id],
            instrument_type_ids=[data["pcr"].id],
            microorganism_ids=[data["organism"].id],
        ),
    )
    assert result.total == 1
    assert result.items[0].matched_analyses[0].targets[0].scientific_name == "SARS-CoV-2"


def test_cross_institution_analysis_instrument_link_is_rejected(db: Session) -> None:
    data = _build_scenario(db)
    try:
        link_analysis_instrument(
            db,
            institution_analysis=data["first_offering"],
            institution_instrument=data["second_pcr"],
        )
    except ValueError as error:
        assert "same institution" in str(error)
    else:
        raise AssertionError("Cross-institution link should have been rejected")
