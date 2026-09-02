from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class InstitutionSummary(ORMModel):
    id: int
    name: str
    slug: str
    city: str
    country: str


class InstrumentMatch(BaseModel):
    id: int
    instrument_type_id: int
    type_name: str
    display_name: str | None
    manufacturer: str | None
    model: str | None
    status: str


class TargetMatch(BaseModel):
    id: int
    scientific_name: str


class AnalysisMatch(BaseModel):
    id: int
    analysis_type_id: int
    type_name: str
    public_name: str | None
    availability: str
    turnaround_days: int | None
    instruments: list[InstrumentMatch]
    targets: list[TargetMatch]


class CapabilityResult(BaseModel):
    institution: InstitutionSummary
    matched_instruments: list[InstrumentMatch]
    matched_analyses: list[AnalysisMatch]


class CapabilitySearchResponse(BaseModel):
    items: list[CapabilityResult]
    total: int
    limit: int
    offset: int


class CatalogItem(ORMModel):
    id: int
    name: str


class MicroorganismItem(ORMModel):
    id: int
    scientific_name: str
    common_name: str | None

