import pytest
from sqlalchemy.orm import Session

from app.modules.catalog.models import (
    AnalysisType,
    Institution,
    InstitutionAnalysis,
    InstitutionInstrument,
    InstrumentType,
    Researcher,
)
from app.modules.catalog.service import (
    CapabilityFilters,
    link_analysis_researcher,
    search_capabilities,
)


def _build_scenario(db: Session) -> dict[str, object]:
    pcr = InstrumentType(name="PCR System")
    analysis_type = AnalysisType(name="PCR analysis")
    first = Institution(
        name="First Institute", slug="first", city="Belgrade", country="Serbia", status="active"
    )
    second = Institution(
        name="Second Institute", slug="second", city="Novi Sad", country="Serbia", status="active"
    )
    db.add_all([pcr, analysis_type, first, second])
    db.flush()

    linked = Researcher(institution_id=first.id, full_name="Linked Researcher", status="active")
    unlinked = Researcher(
        institution_id=first.id, full_name="Unlinked Researcher", status="active"
    )
    other = Researcher(institution_id=second.id, full_name="Other Researcher", status="active")
    db.add_all([linked, unlinked, other])
    db.flush()

    offering = InstitutionAnalysis(
        institution_id=first.id, analysis_type_id=analysis_type.id, availability="available"
    )
    other_offering = InstitutionAnalysis(
        institution_id=second.id, analysis_type_id=analysis_type.id, availability="available"
    )
    db.add_all([offering, other_offering])
    db.flush()
    link_analysis_researcher(
        db, institution_analysis=offering, researcher=linked, role="lead"
    )
    db.flush()

    return {
        "analysis_type": analysis_type,
        "first": first,
        "second": second,
        "linked": linked,
        "unlinked": unlinked,
        "other": other,
        "offering": offering,
    }


def test_researcher_only_search_finds_the_employing_institution(db: Session) -> None:
    scenario = _build_scenario(db)

    response = search_capabilities(
        db, CapabilityFilters(researcher_ids=[scenario["linked"].id])
    )

    assert response.total == 1
    result = response.items[0]
    assert result.institution.id == scenario["first"].id
    assert [person.full_name for person in result.matched_researchers] == ["Linked Researcher"]


def test_analysis_and_researcher_require_a_direct_offering_link(db: Session) -> None:
    scenario = _build_scenario(db)

    linked = search_capabilities(
        db,
        CapabilityFilters(
            analysis_type_ids=[scenario["analysis_type"].id],
            researcher_ids=[scenario["linked"].id],
        ),
    )
    assert [item.institution.id for item in linked.items] == [scenario["first"].id]
    assert linked.items[0].matched_analyses[0].researchers[0].role == "lead"

    unlinked = search_capabilities(
        db,
        CapabilityFilters(
            analysis_type_ids=[scenario["analysis_type"].id],
            researcher_ids=[scenario["unlinked"].id],
        ),
    )
    assert unlinked.total == 0


def test_a_researcher_cannot_be_linked_to_another_institutions_analysis(db: Session) -> None:
    scenario = _build_scenario(db)

    with pytest.raises(ValueError):
        link_analysis_researcher(
            db,
            institution_analysis=scenario["offering"],
            researcher=scenario["other"],
        )


def test_inactive_researchers_are_hidden_from_public_results(db: Session) -> None:
    scenario = _build_scenario(db)
    scenario["linked"].status = "inactive"
    db.flush()

    response = search_capabilities(db, CapabilityFilters())

    first = next(item for item in response.items if item.institution.id == scenario["first"].id)
    assert [person.full_name for person in first.matched_researchers] == ["Unlinked Researcher"]
    assert first.matched_analyses[0].researchers == []


def test_analyses_still_report_their_instruments_alongside_researchers(db: Session) -> None:
    scenario = _build_scenario(db)
    instrument = InstitutionInstrument(
        institution_id=scenario["first"].id,
        instrument_type_id=db.query(InstrumentType).one().id,
        status="operational",
    )
    db.add(instrument)
    db.flush()

    response = search_capabilities(
        db, CapabilityFilters(researcher_ids=[scenario["linked"].id])
    )

    result = response.items[0]
    assert [item.id for item in result.matched_instruments] == [instrument.id]
