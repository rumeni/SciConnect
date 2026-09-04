from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class ResearcherMatch(BaseModel):
    id: int
    full_name: str
    title: str | None
    email: str | None
    orcid: str | None
    expertise: str | None
    status: str
    role: str | None = None


class AnalysisMatch(BaseModel):
    id: int
    analysis_type_id: int
    type_name: str
    public_name: str | None
    availability: str
    turnaround_days: int | None
    instruments: list[InstrumentMatch]
    targets: list[TargetMatch]
    researchers: list[ResearcherMatch]


class CapabilityResult(BaseModel):
    institution: InstitutionSummary
    matched_instruments: list[InstrumentMatch]
    matched_analyses: list[AnalysisMatch]
    matched_researchers: list[ResearcherMatch]


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


class ResearcherItem(ORMModel):
    id: int
    institution_id: int
    full_name: str
    title: str | None
    email: str | None
    orcid: str | None
    expertise: str | None
    status: str


class InstitutionInstrumentItem(ORMModel):
    id: int
    institution_id: int
    instrument_type_id: int
    display_name: str | None
    manufacturer: str | None
    model: str | None
    status: str


class InstitutionAnalysisItem(ORMModel):
    id: int
    institution_id: int
    analysis_type_id: int
    public_name: str | None
    description: str | None
    turnaround_days: int | None
    availability: str


class InstitutionDetail(InstitutionSummary):
    description: str | None
    website: str | None
    contact_email: str | None
    status: str


class InstitutionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    description: str | None = None
    city: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=120)
    website: str | None = Field(default=None, max_length=500)
    contact_email: str | None = Field(default=None, max_length=320)
    status: Literal["draft", "active", "archived"] = "active"


class CatalogTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class MicroorganismCreate(BaseModel):
    scientific_name: str = Field(min_length=1, max_length=240)
    common_name: str | None = Field(default=None, max_length=240)
    description: str | None = None


class ResearcherCreate(BaseModel):
    institution_id: int
    full_name: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=320)
    orcid: str | None = Field(default=None, max_length=40)
    expertise: str | None = None
    status: Literal["active", "inactive", "archived"] = "active"


class InstitutionInstrumentCreate(BaseModel):
    institution_id: int
    instrument_type_id: int
    display_name: str | None = Field(default=None, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=160)
    model: str | None = Field(default=None, max_length=160)
    access_notes: str | None = None
    status: Literal["operational", "maintenance", "unavailable", "archived"] = "operational"


class InstitutionAnalysisCreate(BaseModel):
    institution_id: int
    analysis_type_id: int
    public_name: str | None = Field(default=None, max_length=240)
    description: str | None = None
    turnaround_days: int | None = Field(default=None, gt=0)
    availability: Literal["available", "limited", "unavailable", "archived"] = "available"


class AnalysisInstrumentLinkCreate(BaseModel):
    institution_instrument_id: int
    usage: Literal["required", "optional", "alternative"] = "required"


class AnalysisTargetLinkCreate(BaseModel):
    microorganism_id: int


class AnalysisResearcherLinkCreate(BaseModel):
    researcher_id: int
    role: Literal["lead", "contributor", "contact"] = "contributor"


class LinkAck(BaseModel):
    institution_analysis_id: int
    linked_id: int
    detail: str
