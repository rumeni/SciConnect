from dataclasses import dataclass, field

from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalog.models import (
    Institution,
    InstitutionAnalysis,
    InstitutionAnalysisInstrument,
    InstitutionAnalysisTarget,
    InstitutionInstrument,
)
from app.modules.catalog.schemas import (
    AnalysisMatch,
    CapabilityResult,
    CapabilitySearchResponse,
    InstitutionSummary,
    InstrumentMatch,
    TargetMatch,
)


@dataclass(frozen=True)
class CapabilityFilters:
    institution_ids: list[int] = field(default_factory=list)
    instrument_type_ids: list[int] = field(default_factory=list)
    analysis_type_ids: list[int] = field(default_factory=list)
    microorganism_ids: list[int] = field(default_factory=list)
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
        query = query.where(exists(offering))
    elif filters.instrument_type_ids:
        query = query.where(
            exists().where(
                InstitutionInstrument.institution_id == Institution.id,
                InstitutionInstrument.instrument_type_id.in_(filters.instrument_type_ids),
                InstitutionInstrument.status == "operational",
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
        base.options(
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
        )
        .order_by(Institution.name)
        .limit(limit)
        .offset(offset)
    )
    institutions = db.scalars(query).unique().all()

    results: list[CapabilityResult] = []
    for institution in institutions:
        matched_inventory = [
            item
            for item in institution.instruments
            if item.status == "operational"
            and (
                not filters.instrument_type_ids
                or item.instrument_type_id in filters.instrument_type_ids
            )
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
                )
            )

        results.append(
            CapabilityResult(
                institution=InstitutionSummary.model_validate(institution),
                matched_instruments=[_instrument_match(item) for item in matched_inventory],
                matched_analyses=matched_analyses,
            )
        )

    return CapabilitySearchResponse(items=results, total=total, limit=limit, offset=offset)


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
