from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.catalog.models import AnalysisType, Institution, InstrumentType, Microorganism
from app.modules.catalog.schemas import (
    CapabilitySearchResponse,
    CatalogItem,
    InstitutionSummary,
    MicroorganismItem,
)
from app.modules.catalog.service import CapabilityFilters, search_capabilities

router = APIRouter(prefix="/api/v1")
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/catalog/institutions", response_model=list[InstitutionSummary])
def list_institutions(db: DbSession) -> list[Institution]:
    query = (
        select(Institution)
        .where(Institution.status == "active")
        .order_by(Institution.name)
    )
    return list(db.scalars(query))


@router.get("/capabilities/search", response_model=CapabilitySearchResponse)
def capability_search(
    db: DbSession,
    institution_ids: Annotated[list[int] | None, Query()] = None,
    instrument_type_ids: Annotated[list[int] | None, Query()] = None,
    analysis_type_ids: Annotated[list[int] | None, Query()] = None,
    microorganism_ids: Annotated[list[int] | None, Query()] = None,
    country: str | None = None,
    city: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CapabilitySearchResponse:
    filters = CapabilityFilters(
        institution_ids=institution_ids or [],
        instrument_type_ids=instrument_type_ids or [],
        analysis_type_ids=analysis_type_ids or [],
        microorganism_ids=microorganism_ids or [],
        country=country,
        city=city,
    )
    return search_capabilities(db, filters, limit=limit, offset=offset)


@router.get("/catalog/instrument-types", response_model=list[CatalogItem])
def list_instrument_types(db: DbSession) -> list[InstrumentType]:
    return list(db.scalars(select(InstrumentType).order_by(InstrumentType.name)))


@router.get("/catalog/analysis-types", response_model=list[CatalogItem])
def list_analysis_types(db: DbSession) -> list[AnalysisType]:
    return list(db.scalars(select(AnalysisType).order_by(AnalysisType.name)))


@router.get("/catalog/microorganisms", response_model=list[MicroorganismItem])
def list_microorganisms(db: DbSession) -> list[Microorganism]:
    return list(db.scalars(select(Microorganism).order_by(Microorganism.scientific_name)))
