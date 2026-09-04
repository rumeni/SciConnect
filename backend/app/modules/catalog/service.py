import re
from dataclasses import dataclass, field, replace

from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalog.geocoding import Geocoder, address_query, no_geocoder
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
    AnalysisMatch,
    CapabilityResult,
    CapabilitySearchResponse,
    FilterOption,
    FilterOptions,
    InstitutionAnalysisCreate,
    InstitutionCreate,
    InstitutionInstrumentCreate,
    InstitutionSummary,
    InstrumentMatch,
    MicroorganismCreate,
    ResearcherCreate,
    ResearcherMatch,
    TargetMatch,
)


class DomainError(Exception):
    """A write was rejected because it would break a capability invariant."""


class NotFoundError(DomainError):
    """A referenced record does not exist."""


class ConflictError(DomainError):
    """A record or link with the same identity already exists."""


@dataclass(frozen=True)
class CapabilityFilters:
    institution_ids: list[int] = field(default_factory=list)
    instrument_type_ids: list[int] = field(default_factory=list)
    analysis_type_ids: list[int] = field(default_factory=list)
    microorganism_ids: list[int] = field(default_factory=list)
    researcher_ids: list[int] = field(default_factory=list)
    country: str | None = None
    city: str | None = None


def _instrument_match(instrument: InstitutionInstrument) -> InstrumentMatch:
    return InstrumentMatch(
        id=instrument.id,
        instrument_type_id=instrument.instrument_type_id,
        type_name=instrument.instrument_type.name,
        display_name=instrument.display_name,
        manufacturer=instrument.manufacturer,
        model=instrument.model,
        status=instrument.status,
    )


def _researcher_match(researcher: Researcher, role: str | None = None) -> ResearcherMatch:
    return ResearcherMatch(
        id=researcher.id,
        full_name=researcher.full_name,
        title=researcher.title,
        email=researcher.email,
        orcid=researcher.orcid,
        expertise=researcher.expertise,
        status=researcher.status,
        role=role,
    )


def _base_query(filters: CapabilityFilters) -> Select[tuple[Institution]]:
    query = select(Institution).where(Institution.status == "active")

    if filters.institution_ids:
        query = query.where(Institution.id.in_(filters.institution_ids))
    if filters.country:
        query = query.where(Institution.country.ilike(filters.country))
    if filters.city:
        query = query.where(Institution.city.ilike(filters.city))

    has_analysis_filter = bool(filters.analysis_type_ids or filters.microorganism_ids)
    if has_analysis_filter:
        offering = select(InstitutionAnalysis.id).where(
            InstitutionAnalysis.institution_id == Institution.id,
            InstitutionAnalysis.availability.in_(["available", "limited"]),
        )
        if filters.analysis_type_ids:
            offering = offering.where(
                InstitutionAnalysis.analysis_type_id.in_(filters.analysis_type_ids)
            )
        if filters.microorganism_ids:
            offering = offering.where(
                exists().where(
                    InstitutionAnalysisTarget.institution_analysis_id == InstitutionAnalysis.id,
                    InstitutionAnalysisTarget.microorganism_id.in_(filters.microorganism_ids),
                )
            )
        if filters.instrument_type_ids:
            offering = offering.where(
                exists()
                .where(
                    InstitutionAnalysisInstrument.institution_analysis_id
                    == InstitutionAnalysis.id,
                    InstitutionAnalysisInstrument.institution_instrument_id
                    == InstitutionInstrument.id,
                    InstitutionInstrument.instrument_type_id.in_(filters.instrument_type_ids),
                    InstitutionInstrument.status == "operational",
                )
                .correlate(InstitutionAnalysis)
            )
        if filters.researcher_ids:
            offering = offering.where(
                exists()
                .where(
                    InstitutionAnalysisResearcher.institution_analysis_id
                    == InstitutionAnalysis.id,
                    InstitutionAnalysisResearcher.researcher_id == Researcher.id,
                    Researcher.id.in_(filters.researcher_ids),
                    Researcher.status == "active",
                )
                .correlate(InstitutionAnalysis)
            )
        query = query.where(exists(offering))
    else:
        if filters.instrument_type_ids:
            query = query.where(
                exists().where(
                    InstitutionInstrument.institution_id == Institution.id,
                    InstitutionInstrument.instrument_type_id.in_(filters.instrument_type_ids),
                    InstitutionInstrument.status == "operational",
                )
            )
        if filters.researcher_ids:
            query = query.where(
                exists().where(
                    Researcher.institution_id == Institution.id,
                    Researcher.id.in_(filters.researcher_ids),
                    Researcher.status == "active",
                )
            )

    return query


def search_capabilities(
    db: Session,
    filters: CapabilityFilters,
    *,
    limit: int = 20,
    offset: int = 0,
) -> CapabilitySearchResponse:
    base = _base_query(filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    query = (
        base.options(*_capability_loads())
        .order_by(Institution.name)
        .limit(limit)
        .offset(offset)
    )
    institutions = db.scalars(query).unique().all()

    results = [_result_for(institution, filters) for institution in institutions]

    return CapabilitySearchResponse(items=results, total=total, limit=limit, offset=offset)


def _capability_loads() -> list:
    return [
        selectinload(Institution.instruments).selectinload(
            InstitutionInstrument.instrument_type
        ),
        selectinload(Institution.analyses).selectinload(InstitutionAnalysis.analysis_type),
        selectinload(Institution.analyses)
        .selectinload(InstitutionAnalysis.instrument_links)
        .selectinload(InstitutionAnalysisInstrument.institution_instrument)
        .selectinload(InstitutionInstrument.instrument_type),
        selectinload(Institution.analyses)
        .selectinload(InstitutionAnalysis.target_links)
        .selectinload(InstitutionAnalysisTarget.microorganism),
        selectinload(Institution.analyses)
        .selectinload(InstitutionAnalysis.researcher_links)
        .selectinload(InstitutionAnalysisResearcher.researcher),
        selectinload(Institution.researchers),
    ]


def _result_for(institution: Institution, filters: CapabilityFilters) -> CapabilityResult:
    matched_inventory = [
        item
        for item in institution.instruments
        if item.status == "operational"
        and (
            not filters.instrument_type_ids
            or item.instrument_type_id in filters.instrument_type_ids
        )
    ]

    matched_staff = [
        person
        for person in institution.researchers
        if person.status == "active"
        and (not filters.researcher_ids or person.id in filters.researcher_ids)
    ]

    matched_analyses: list[AnalysisMatch] = []
    for offering in institution.analyses:
        if offering.availability not in {"available", "limited"}:
            continue
        if (
            filters.analysis_type_ids
            and offering.analysis_type_id not in filters.analysis_type_ids
        ):
            continue
        targets = [link.microorganism for link in offering.target_links]
        if filters.microorganism_ids and not any(
            target.id in filters.microorganism_ids for target in targets
        ):
            continue

        offering_instruments = [
            link.institution_instrument
            for link in offering.instrument_links
            if link.institution_instrument.status == "operational"
        ]
        if filters.instrument_type_ids:
            offering_instruments = [
                item
                for item in offering_instruments
                if item.instrument_type_id in filters.instrument_type_ids
            ]
            if not offering_instruments:
                continue

        offering_researchers = [
            (link.researcher, link.role)
            for link in offering.researcher_links
            if link.researcher.status == "active"
        ]
        if filters.researcher_ids:
            offering_researchers = [
                entry
                for entry in offering_researchers
                if entry[0].id in filters.researcher_ids
            ]
            if not offering_researchers:
                continue

        matched_analyses.append(
            AnalysisMatch(
                id=offering.id,
                analysis_type_id=offering.analysis_type_id,
                type_name=offering.analysis_type.name,
                public_name=offering.public_name,
                availability=offering.availability,
                turnaround_days=offering.turnaround_days,
                instruments=[_instrument_match(item) for item in offering_instruments],
                targets=[
                    TargetMatch(id=target.id, scientific_name=target.scientific_name)
                    for target in targets
                ],
                researchers=[
                    _researcher_match(person, role) for person, role in offering_researchers
                ],
            )
        )

    return CapabilityResult(
        institution=InstitutionSummary.model_validate(institution),
        matched_instruments=[_instrument_match(item) for item in matched_inventory],
        matched_analyses=matched_analyses,
        matched_researchers=[_researcher_match(person) for person in matched_staff],
    )


def link_analysis_instrument(
    db: Session,
    *,
    institution_analysis: InstitutionAnalysis,
    institution_instrument: InstitutionInstrument,
    usage: str = "required",
) -> InstitutionAnalysisInstrument:
    if institution_analysis.institution_id != institution_instrument.institution_id:
        raise ValueError("Analysis and instrument must belong to the same institution")
    link = InstitutionAnalysisInstrument(
        institution_analysis_id=institution_analysis.id,
        institution_instrument_id=institution_instrument.id,
        institution_id=institution_analysis.institution_id,
        usage=usage,
    )
    db.add(link)
    return link


def link_analysis_researcher(
    db: Session,
    *,
    institution_analysis: InstitutionAnalysis,
    researcher: Researcher,
    role: str = "contributor",
) -> InstitutionAnalysisResearcher:
    if institution_analysis.institution_id != researcher.institution_id:
        raise ValueError("Analysis and researcher must belong to the same institution")
    link = InstitutionAnalysisResearcher(
        institution_analysis_id=institution_analysis.id,
        researcher_id=researcher.id,
        institution_id=institution_analysis.institution_id,
        role=role,
    )
    db.add(link)
    return link


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "institution"


def _get_or_404(db: Session, model: type, record_id: int, label: str):
    record = db.get(model, record_id)
    if record is None:
        raise NotFoundError(f"{label} {record_id} does not exist")
    return record


def create_institution(
    db: Session,
    payload: InstitutionCreate,
    geocoder: Geocoder = no_geocoder,
) -> Institution:
    slug = payload.slug or slugify(payload.name)
    if db.scalar(select(Institution.id).where(Institution.slug == slug)) is not None:
        raise ConflictError(f"Institution slug '{slug}' is already taken")

    fields = payload.model_dump(exclude={"slug"})
    if fields["latitude"] is None:
        located = locate(payload, geocoder)
        if located is not None:
            fields["latitude"] = located.latitude
            fields["longitude"] = located.longitude

    institution = Institution(**fields, slug=slug)
    db.add(institution)
    db.flush()
    return institution


def locate(payload: InstitutionCreate, geocoder: Geocoder):
    """Find coordinates for a written address. Returns None when it cannot be placed."""
    query = address_query(payload.address, payload.city, payload.country)
    return geocoder(query) if query else None


def create_instrument_type(db: Session, name: str, description: str | None) -> InstrumentType:
    if db.scalar(select(InstrumentType.id).where(InstrumentType.name == name)) is not None:
        raise ConflictError(f"Instrument type '{name}' already exists")
    record = InstrumentType(name=name, description=description)
    db.add(record)
    db.flush()
    return record


def create_analysis_type(db: Session, name: str, description: str | None) -> AnalysisType:
    if db.scalar(select(AnalysisType.id).where(AnalysisType.name == name)) is not None:
        raise ConflictError(f"Analysis type '{name}' already exists")
    record = AnalysisType(name=name, description=description)
    db.add(record)
    db.flush()
    return record


def create_microorganism(db: Session, payload: MicroorganismCreate) -> Microorganism:
    existing = select(Microorganism.id).where(
        Microorganism.scientific_name == payload.scientific_name
    )
    if db.scalar(existing) is not None:
        raise ConflictError(f"Microorganism '{payload.scientific_name}' already exists")
    record = Microorganism(**payload.model_dump())
    db.add(record)
    db.flush()
    return record


def create_researcher(db: Session, payload: ResearcherCreate) -> Researcher:
    _get_or_404(db, Institution, payload.institution_id, "Institution")
    if payload.orcid and db.scalar(select(Researcher.id).where(Researcher.orcid == payload.orcid)):
        raise ConflictError(f"A researcher with ORCID '{payload.orcid}' already exists")
    record = Researcher(**payload.model_dump())
    db.add(record)
    db.flush()
    return record


def create_institution_instrument(
    db: Session, payload: InstitutionInstrumentCreate
) -> InstitutionInstrument:
    _get_or_404(db, Institution, payload.institution_id, "Institution")
    _get_or_404(db, InstrumentType, payload.instrument_type_id, "Instrument type")
    record = InstitutionInstrument(**payload.model_dump())
    db.add(record)
    db.flush()
    return record


def create_institution_analysis(
    db: Session, payload: InstitutionAnalysisCreate
) -> InstitutionAnalysis:
    _get_or_404(db, Institution, payload.institution_id, "Institution")
    _get_or_404(db, AnalysisType, payload.analysis_type_id, "Analysis type")
    duplicate = select(InstitutionAnalysis.id).where(
        InstitutionAnalysis.institution_id == payload.institution_id,
        InstitutionAnalysis.analysis_type_id == payload.analysis_type_id,
    )
    if db.scalar(duplicate) is not None:
        raise ConflictError("This institution already offers that analysis type")
    record = InstitutionAnalysis(**payload.model_dump())
    db.add(record)
    db.flush()
    return record


def add_analysis_instrument(
    db: Session, analysis_id: int, instrument_id: int, usage: str
) -> InstitutionAnalysisInstrument:
    analysis = _get_or_404(db, InstitutionAnalysis, analysis_id, "Institution analysis")
    instrument = _get_or_404(db, InstitutionInstrument, instrument_id, "Institution instrument")
    if db.get(InstitutionAnalysisInstrument, (analysis_id, instrument_id)) is not None:
        raise ConflictError("That instrument is already linked to this analysis")
    try:
        link = link_analysis_instrument(
            db, institution_analysis=analysis, institution_instrument=instrument, usage=usage
        )
    except ValueError as error:
        raise DomainError(str(error)) from error
    db.flush()
    return link


def add_analysis_researcher(
    db: Session, analysis_id: int, researcher_id: int, role: str
) -> InstitutionAnalysisResearcher:
    analysis = _get_or_404(db, InstitutionAnalysis, analysis_id, "Institution analysis")
    researcher = _get_or_404(db, Researcher, researcher_id, "Researcher")
    if db.get(InstitutionAnalysisResearcher, (analysis_id, researcher_id)) is not None:
        raise ConflictError("That researcher is already linked to this analysis")
    try:
        link = link_analysis_researcher(
            db, institution_analysis=analysis, researcher=researcher, role=role
        )
    except ValueError as error:
        raise DomainError(str(error)) from error
    db.flush()
    return link


def add_analysis_target(
    db: Session, analysis_id: int, microorganism_id: int
) -> InstitutionAnalysisTarget:
    _get_or_404(db, InstitutionAnalysis, analysis_id, "Institution analysis")
    _get_or_404(db, Microorganism, microorganism_id, "Microorganism")
    if db.get(InstitutionAnalysisTarget, (analysis_id, microorganism_id)) is not None:
        raise ConflictError("That target organism is already linked to this analysis")
    link = InstitutionAnalysisTarget(
        institution_analysis_id=analysis_id, microorganism_id=microorganism_id
    )
    db.add(link)
    db.flush()
    return link


# --- Filter options ---------------------------------------------------------
# Each dropdown offers only values that still lead somewhere. Options for one
# category are computed with every *other* selection applied, so the category's
# own choice can still be changed while the rest stay consistent.
#
# The options are harvested from real search results rather than from separate
# queries, which guarantees that picking any offered value returns at least one
# institution. That costs one search per category, which is fine at this
# catalog's size but would need reworking into aggregate queries if the number
# of institutions grew large.


def _matching_results(db: Session, filters: CapabilityFilters) -> list[CapabilityResult]:
    query = _base_query(filters).options(*_capability_loads()).order_by(Institution.name)
    return [_result_for(institution, filters) for institution in db.scalars(query).unique()]


def _options(pairs: list[tuple[int, str]]) -> list[FilterOption]:
    found: dict[int, str] = {}
    for identifier, label in pairs:
        found.setdefault(identifier, label)
    return [
        FilterOption(id=identifier, label=label)
        for identifier, label in sorted(found.items(), key=lambda item: item[1].lower())
    ]


def filter_options(db: Session, filters: CapabilityFilters) -> FilterOptions:
    def without(**cleared: list[int]) -> list[CapabilityResult]:
        return _matching_results(db, replace(filters, **cleared))

    institutions = without(institution_ids=[])
    instruments = without(instrument_type_ids=[])
    analyses = without(analysis_type_ids=[])
    organisms = without(microorganism_ids=[])
    researchers = without(researcher_ids=[])

    return FilterOptions(
        institutions=_options(
            [(item.institution.id, item.institution.name) for item in institutions]
        ),
        instrument_types=_options(
            [
                (instrument.instrument_type_id, instrument.type_name)
                for item in instruments
                for instrument in item.matched_instruments
            ]
        ),
        analysis_types=_options(
            [
                (analysis.analysis_type_id, analysis.type_name)
                for item in analyses
                for analysis in item.matched_analyses
            ]
        ),
        microorganisms=_options(
            [
                (target.id, target.scientific_name)
                for item in organisms
                for analysis in item.matched_analyses
                for target in analysis.targets
            ]
        ),
        researchers=_options(
            [
                (person.id, person.full_name)
                for item in researchers
                for person in item.matched_researchers
            ]
        ),
    )
