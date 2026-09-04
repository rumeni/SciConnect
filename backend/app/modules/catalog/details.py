"""Detail views for every entity a search result can display.

A detail view answers "what is this record, and what is it connected to". Each
related record comes back as a small reference carrying the id and label the UI
needs to link one level deeper, plus the role or usage of the relationship
where one exists.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalog.models import (
    AnalysisType,
    Institution,
    InstitutionAnalysis,
    InstitutionAnalysisInstrument,
    InstitutionAnalysisResearcher,
    InstitutionAnalysisTarget,
    InstitutionInstrument,
    InstrumentType,
    Microorganism,
    Researcher,
)
from app.modules.catalog.schemas import (
    AnalysisDetailView,
    AnalysisRef,
    AnalysisTypeDetailView,
    InstitutionDetailView,
    InstitutionRef,
    InstrumentDetailView,
    InstrumentRef,
    InstrumentTypeDetailView,
    MicroorganismDetailView,
    PersonRef,
    ResearcherDetailView,
    TargetRef,
    TypeRef,
)
from app.modules.catalog.service import NotFoundError


def _institution_ref(institution: Institution) -> InstitutionRef:
    return InstitutionRef.model_validate(institution)


def _instrument_ref(
    instrument: InstitutionInstrument, usage: str | None = None
) -> InstrumentRef:
    return InstrumentRef(
        id=instrument.id,
        display_name=instrument.display_name,
        type_name=instrument.instrument_type.name,
        manufacturer=instrument.manufacturer,
        model=instrument.model,
        status=instrument.status,
        usage=usage,
    )


def _analysis_ref(
    analysis: InstitutionAnalysis,
    *,
    role: str | None = None,
    usage: str | None = None,
    with_institution: bool = False,
) -> AnalysisRef:
    return AnalysisRef(
        id=analysis.id,
        public_name=analysis.public_name,
        type_name=analysis.analysis_type.name,
        availability=analysis.availability,
        turnaround_days=analysis.turnaround_days,
        role=role,
        usage=usage,
        institution=_institution_ref(analysis.institution) if with_institution else None,
    )


def _person_ref(
    researcher: Researcher, *, role: str | None = None, with_institution: bool = False
) -> PersonRef:
    return PersonRef(
        id=researcher.id,
        full_name=researcher.full_name,
        title=researcher.title,
        status=researcher.status,
        role=role,
        institution=_institution_ref(researcher.institution) if with_institution else None,
    )


def _load(db: Session, statement, label: str, record_id: int):
    record = db.scalars(statement).unique().one_or_none()
    if record is None:
        raise NotFoundError(f"{label} {record_id} does not exist")
    return record


def institution_detail(db: Session, institution_id: int) -> InstitutionDetailView:
    institution = _load(
        db,
        select(Institution)
        .where(Institution.id == institution_id)
        .options(
            selectinload(Institution.instruments).selectinload(
                InstitutionInstrument.instrument_type
            ),
            selectinload(Institution.analyses).selectinload(InstitutionAnalysis.analysis_type),
            selectinload(Institution.researchers),
        ),
        "Institution",
        institution_id,
    )
    return InstitutionDetailView(
        id=institution.id,
        name=institution.name,
        slug=institution.slug,
        description=institution.description,
        address=institution.address,
        city=institution.city,
        country=institution.country,
        website=institution.website,
        contact_email=institution.contact_email,
        status=institution.status,
        latitude=institution.latitude,
        longitude=institution.longitude,
        instruments=[_instrument_ref(item) for item in institution.instruments],
        analyses=[_analysis_ref(item) for item in institution.analyses],
        researchers=[_person_ref(person) for person in institution.researchers],
    )


def researcher_detail(db: Session, researcher_id: int) -> ResearcherDetailView:
    researcher = _load(
        db,
        select(Researcher)
        .where(Researcher.id == researcher_id)
        .options(
            selectinload(Researcher.institution),
            selectinload(Researcher.analysis_links)
            .selectinload(InstitutionAnalysisResearcher.institution_analysis)
            .selectinload(InstitutionAnalysis.analysis_type),
        ),
        "Researcher",
        researcher_id,
    )
    return ResearcherDetailView(
        id=researcher.id,
        full_name=researcher.full_name,
        title=researcher.title,
        email=researcher.email,
        orcid=researcher.orcid,
        expertise=researcher.expertise,
        status=researcher.status,
        institution=_institution_ref(researcher.institution),
        analyses=[
            _analysis_ref(link.institution_analysis, role=link.role)
            for link in researcher.analysis_links
        ],
    )


def instrument_detail(db: Session, instrument_id: int) -> InstrumentDetailView:
    instrument = _load(
        db,
        select(InstitutionInstrument)
        .where(InstitutionInstrument.id == instrument_id)
        .options(
            selectinload(InstitutionInstrument.instrument_type),
            selectinload(InstitutionInstrument.institution),
            selectinload(InstitutionInstrument.analysis_links)
            .selectinload(InstitutionAnalysisInstrument.institution_analysis)
            .selectinload(InstitutionAnalysis.analysis_type),
        ),
        "Institution instrument",
        instrument_id,
    )
    return InstrumentDetailView(
        id=instrument.id,
        display_name=instrument.display_name,
        manufacturer=instrument.manufacturer,
        model=instrument.model,
        status=instrument.status,
        access_notes=instrument.access_notes,
        instrument_type=TypeRef.model_validate(instrument.instrument_type),
        institution=_institution_ref(instrument.institution),
        analyses=[
            _analysis_ref(link.institution_analysis, usage=link.usage)
            for link in instrument.analysis_links
        ],
    )


def analysis_detail(db: Session, analysis_id: int) -> AnalysisDetailView:
    analysis = _load(
        db,
        select(InstitutionAnalysis)
        .where(InstitutionAnalysis.id == analysis_id)
        .options(
            selectinload(InstitutionAnalysis.analysis_type),
            selectinload(InstitutionAnalysis.institution),
            selectinload(InstitutionAnalysis.instrument_links)
            .selectinload(InstitutionAnalysisInstrument.institution_instrument)
            .selectinload(InstitutionInstrument.instrument_type),
            selectinload(InstitutionAnalysis.target_links).selectinload(
                InstitutionAnalysisTarget.microorganism
            ),
            selectinload(InstitutionAnalysis.researcher_links).selectinload(
                InstitutionAnalysisResearcher.researcher
            ),
        ),
        "Institution analysis",
        analysis_id,
    )
    return AnalysisDetailView(
        id=analysis.id,
        public_name=analysis.public_name,
        description=analysis.description,
        turnaround_days=analysis.turnaround_days,
        availability=analysis.availability,
        analysis_type=TypeRef.model_validate(analysis.analysis_type),
        institution=_institution_ref(analysis.institution),
        instruments=[
            _instrument_ref(link.institution_instrument, usage=link.usage)
            for link in analysis.instrument_links
        ],
        targets=[TargetRef.model_validate(link.microorganism) for link in analysis.target_links],
        researchers=[
            _person_ref(link.researcher, role=link.role) for link in analysis.researcher_links
        ],
    )


def microorganism_detail(db: Session, microorganism_id: int) -> MicroorganismDetailView:
    organism = _load(
        db,
        select(Microorganism)
        .where(Microorganism.id == microorganism_id)
        .options(
            selectinload(Microorganism.analysis_links)
            .selectinload(InstitutionAnalysisTarget.institution_analysis)
            .selectinload(InstitutionAnalysis.analysis_type),
            selectinload(Microorganism.analysis_links)
            .selectinload(InstitutionAnalysisTarget.institution_analysis)
            .selectinload(InstitutionAnalysis.institution),
        ),
        "Microorganism",
        microorganism_id,
    )
    return MicroorganismDetailView(
        id=organism.id,
        scientific_name=organism.scientific_name,
        common_name=organism.common_name,
        description=organism.description,
        analyses=[
            _analysis_ref(link.institution_analysis, with_institution=True)
            for link in organism.analysis_links
        ],
    )


def _distinct_institutions(institutions: list[Institution]) -> list[InstitutionRef]:
    seen: dict[int, Institution] = {}
    for institution in institutions:
        seen.setdefault(institution.id, institution)
    return [_institution_ref(item) for item in sorted(seen.values(), key=lambda x: x.name)]


def instrument_type_detail(db: Session, type_id: int) -> InstrumentTypeDetailView:
    instrument_type = _load(
        db,
        select(InstrumentType)
        .where(InstrumentType.id == type_id)
        .options(
            selectinload(InstrumentType.institution_instruments).selectinload(
                InstitutionInstrument.institution
            ),
        ),
        "Instrument type",
        type_id,
    )
    units = instrument_type.institution_instruments
    return InstrumentTypeDetailView(
        id=instrument_type.id,
        name=instrument_type.name,
        description=instrument_type.description,
        instruments=[
            InstrumentRef(
                id=unit.id,
                display_name=unit.display_name,
                type_name=instrument_type.name,
                manufacturer=unit.manufacturer,
                model=unit.model,
                status=unit.status,
            )
            for unit in units
        ],
        institutions=_distinct_institutions([unit.institution for unit in units]),
    )


def analysis_type_detail(db: Session, type_id: int) -> AnalysisTypeDetailView:
    analysis_type = _load(
        db,
        select(AnalysisType)
        .where(AnalysisType.id == type_id)
        .options(
            selectinload(AnalysisType.institution_analyses).selectinload(
                InstitutionAnalysis.institution
            ),
        ),
        "Analysis type",
        type_id,
    )
    offerings = analysis_type.institution_analyses
    return AnalysisTypeDetailView(
        id=analysis_type.id,
        name=analysis_type.name,
        description=analysis_type.description,
        analyses=[
            AnalysisRef(
                id=offering.id,
                public_name=offering.public_name,
                type_name=analysis_type.name,
                availability=offering.availability,
                turnaround_days=offering.turnaround_days,
                institution=_institution_ref(offering.institution),
            )
            for offering in offerings
        ],
        institutions=_distinct_institutions(
            [offering.institution for offering in offerings]
        ),
    )
