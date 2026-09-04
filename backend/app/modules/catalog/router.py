from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.catalog import details, service
from app.modules.catalog.geocoding import Geocoder, default_geocoder
from app.modules.catalog.models import (
    AnalysisType,
    Institution,
    InstitutionAnalysis,
    InstitutionInstrument,
    InstrumentType,
    Microorganism,
    Researcher,
)
from app.modules.catalog.schemas import (
    AnalysisDetailView,
    AnalysisInstrumentLinkCreate,
    AnalysisResearcherLinkCreate,
    AnalysisTargetLinkCreate,
    AnalysisTypeDetailView,
    CapabilitySearchResponse,
    CatalogItem,
    CatalogTypeCreate,
    FilterOptions,
    InstitutionAnalysisCreate,
    InstitutionAnalysisItem,
    InstitutionCreate,
    InstitutionDetail,
    InstitutionDetailView,
    InstitutionInstrumentCreate,
    InstitutionInstrumentItem,
    InstitutionSummary,
    InstrumentDetailView,
    InstrumentTypeDetailView,
    LinkAck,
    MicroorganismCreate,
    MicroorganismDetailView,
    MicroorganismItem,
    ResearcherCreate,
    ResearcherDetailView,
    ResearcherItem,
)
from app.modules.catalog.service import (
    CapabilityFilters,
    filter_options,
    search_capabilities,
)

router = APIRouter(prefix="/api/v1")
DbSession = Annotated[Session, Depends(get_db)]
# Injected so tests, and offline deployments, can swap the address lookup out.
AddressLookup = Annotated[Geocoder, Depends(default_geocoder)]


def _commit(db: Session, work):
    """Run a write, translating domain errors into HTTP responses."""
    try:
        result = work()
    except service.NotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except service.ConflictError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except service.DomainError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    db.commit()
    return result


@router.get("/catalog/institutions", response_model=list[InstitutionSummary])
def list_institutions(db: DbSession) -> list[Institution]:
    query = (
        select(Institution)
        .where(Institution.status == "active")
        .order_by(Institution.name)
    )
    return list(db.scalars(query))


def selected_filters(
    institution_ids: Annotated[list[int] | None, Query()] = None,
    instrument_type_ids: Annotated[list[int] | None, Query()] = None,
    analysis_type_ids: Annotated[list[int] | None, Query()] = None,
    microorganism_ids: Annotated[list[int] | None, Query()] = None,
    researcher_ids: Annotated[list[int] | None, Query()] = None,
    country: str | None = None,
    city: str | None = None,
) -> CapabilityFilters:
    return CapabilityFilters(
        institution_ids=institution_ids or [],
        instrument_type_ids=instrument_type_ids or [],
        analysis_type_ids=analysis_type_ids or [],
        microorganism_ids=microorganism_ids or [],
        researcher_ids=researcher_ids or [],
        country=country,
        city=city,
    )


Filters = Annotated[CapabilityFilters, Depends(selected_filters)]


@router.get("/capabilities/search", response_model=CapabilitySearchResponse)
def capability_search(
    db: DbSession,
    filters: Filters,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CapabilitySearchResponse:
    return search_capabilities(db, filters, limit=limit, offset=offset)


@router.get("/capabilities/filter-options", response_model=FilterOptions)
def capability_filter_options(db: DbSession, filters: Filters) -> FilterOptions:
    """The values each filter can still usefully offer, given the other choices."""
    return filter_options(db, filters)


@router.get("/catalog/instrument-types", response_model=list[CatalogItem])
def list_instrument_types(db: DbSession) -> list[InstrumentType]:
    return list(db.scalars(select(InstrumentType).order_by(InstrumentType.name)))


@router.get("/catalog/analysis-types", response_model=list[CatalogItem])
def list_analysis_types(db: DbSession) -> list[AnalysisType]:
    return list(db.scalars(select(AnalysisType).order_by(AnalysisType.name)))


@router.get("/catalog/microorganisms", response_model=list[MicroorganismItem])
def list_microorganisms(db: DbSession) -> list[Microorganism]:
    return list(db.scalars(select(Microorganism).order_by(Microorganism.scientific_name)))


@router.get("/catalog/researchers", response_model=list[ResearcherItem])
def list_researchers(db: DbSession, institution_id: int | None = None) -> list[Researcher]:
    query = select(Researcher).where(Researcher.status == "active")
    if institution_id is not None:
        query = query.where(Researcher.institution_id == institution_id)
    return list(db.scalars(query.order_by(Researcher.full_name)))


@router.get("/catalog/institution-instruments", response_model=list[InstitutionInstrumentItem])
def list_institution_instruments(
    db: DbSession, institution_id: int | None = None
) -> list[InstitutionInstrument]:
    query = select(InstitutionInstrument)
    if institution_id is not None:
        query = query.where(InstitutionInstrument.institution_id == institution_id)
    return list(db.scalars(query.order_by(InstitutionInstrument.id)))


@router.get("/catalog/institution-analyses", response_model=list[InstitutionAnalysisItem])
def list_institution_analyses(
    db: DbSession, institution_id: int | None = None
) -> list[InstitutionAnalysis]:
    query = select(InstitutionAnalysis)
    if institution_id is not None:
        query = query.where(InstitutionAnalysis.institution_id == institution_id)
    return list(db.scalars(query.order_by(InstitutionAnalysis.id)))


# --- Detail views -----------------------------------------------------------
# Every entity a search result displays can be opened on its own, with the
# records it is connected to. Unlike public search these do not hide archived
# records: the status is returned so the caller can show it.


def _detail(work):
    try:
        return work()
    except service.NotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


@router.get("/catalog/institutions/{institution_id}", response_model=InstitutionDetailView)
def institution_detail(db: DbSession, institution_id: int) -> InstitutionDetailView:
    return _detail(lambda: details.institution_detail(db, institution_id))


@router.get("/catalog/researchers/{researcher_id}", response_model=ResearcherDetailView)
def researcher_detail(db: DbSession, researcher_id: int) -> ResearcherDetailView:
    return _detail(lambda: details.researcher_detail(db, researcher_id))


@router.get(
    "/catalog/institution-instruments/{instrument_id}", response_model=InstrumentDetailView
)
def instrument_detail(db: DbSession, instrument_id: int) -> InstrumentDetailView:
    return _detail(lambda: details.instrument_detail(db, instrument_id))


@router.get("/catalog/institution-analyses/{analysis_id}", response_model=AnalysisDetailView)
def analysis_detail(db: DbSession, analysis_id: int) -> AnalysisDetailView:
    return _detail(lambda: details.analysis_detail(db, analysis_id))


@router.get(
    "/catalog/microorganisms/{microorganism_id}", response_model=MicroorganismDetailView
)
def microorganism_detail(db: DbSession, microorganism_id: int) -> MicroorganismDetailView:
    return _detail(lambda: details.microorganism_detail(db, microorganism_id))


@router.get("/catalog/instrument-types/{type_id}", response_model=InstrumentTypeDetailView)
def instrument_type_detail(db: DbSession, type_id: int) -> InstrumentTypeDetailView:
    return _detail(lambda: details.instrument_type_detail(db, type_id))


@router.get("/catalog/analysis-types/{type_id}", response_model=AnalysisTypeDetailView)
def analysis_type_detail(db: DbSession, type_id: int) -> AnalysisTypeDetailView:
    return _detail(lambda: details.analysis_type_detail(db, type_id))


@router.post(
    "/catalog/institutions",
    response_model=InstitutionDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_institution(
    db: DbSession, payload: InstitutionCreate, geocoder: AddressLookup
) -> Institution:
    return _commit(db, lambda: service.create_institution(db, payload, geocoder))


@router.post(
    "/catalog/instrument-types",
    response_model=CatalogItem,
    status_code=status.HTTP_201_CREATED,
)
def create_instrument_type(db: DbSession, payload: CatalogTypeCreate) -> InstrumentType:
    return _commit(
        db, lambda: service.create_instrument_type(db, payload.name, payload.description)
    )


@router.post(
    "/catalog/analysis-types",
    response_model=CatalogItem,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_type(db: DbSession, payload: CatalogTypeCreate) -> AnalysisType:
    return _commit(
        db, lambda: service.create_analysis_type(db, payload.name, payload.description)
    )


@router.post(
    "/catalog/microorganisms",
    response_model=MicroorganismItem,
    status_code=status.HTTP_201_CREATED,
)
def create_microorganism(db: DbSession, payload: MicroorganismCreate) -> Microorganism:
    return _commit(db, lambda: service.create_microorganism(db, payload))


@router.post(
    "/catalog/researchers",
    response_model=ResearcherItem,
    status_code=status.HTTP_201_CREATED,
)
def create_researcher(db: DbSession, payload: ResearcherCreate) -> Researcher:
    return _commit(db, lambda: service.create_researcher(db, payload))


@router.post(
    "/catalog/institution-instruments",
    response_model=InstitutionInstrumentItem,
    status_code=status.HTTP_201_CREATED,
)
def create_institution_instrument(
    db: DbSession, payload: InstitutionInstrumentCreate
) -> InstitutionInstrument:
    return _commit(db, lambda: service.create_institution_instrument(db, payload))


@router.post(
    "/catalog/institution-analyses",
    response_model=InstitutionAnalysisItem,
    status_code=status.HTTP_201_CREATED,
)
def create_institution_analysis(
    db: DbSession, payload: InstitutionAnalysisCreate
) -> InstitutionAnalysis:
    return _commit(db, lambda: service.create_institution_analysis(db, payload))


@router.post(
    "/institution-analyses/{analysis_id}/instruments",
    response_model=LinkAck,
    status_code=status.HTTP_201_CREATED,
)
def link_instrument(
    db: DbSession, analysis_id: int, payload: AnalysisInstrumentLinkCreate
) -> LinkAck:
    _commit(
        db,
        lambda: service.add_analysis_instrument(
            db, analysis_id, payload.institution_instrument_id, payload.usage
        ),
    )
    return LinkAck(
        institution_analysis_id=analysis_id,
        linked_id=payload.institution_instrument_id,
        detail=f"Instrument linked as {payload.usage}",
    )


@router.post(
    "/institution-analyses/{analysis_id}/targets",
    response_model=LinkAck,
    status_code=status.HTTP_201_CREATED,
)
def link_target(db: DbSession, analysis_id: int, payload: AnalysisTargetLinkCreate) -> LinkAck:
    _commit(db, lambda: service.add_analysis_target(db, analysis_id, payload.microorganism_id))
    return LinkAck(
        institution_analysis_id=analysis_id,
        linked_id=payload.microorganism_id,
        detail="Target organism linked",
    )


@router.post(
    "/institution-analyses/{analysis_id}/researchers",
    response_model=LinkAck,
    status_code=status.HTTP_201_CREATED,
)
def link_researcher(
    db: DbSession, analysis_id: int, payload: AnalysisResearcherLinkCreate
) -> LinkAck:
    _commit(
        db,
        lambda: service.add_analysis_researcher(
            db, analysis_id, payload.researcher_id, payload.role
        ),
    )
    return LinkAck(
        institution_analysis_id=analysis_id,
        linked_id=payload.researcher_id,
        detail=f"Researcher linked as {payload.role}",
    )
