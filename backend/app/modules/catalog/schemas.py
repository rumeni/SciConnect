from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class FilterOption(BaseModel):
    id: int
    label: str


class FilterOptions(BaseModel):
    """The values still worth offering in each filter, given the current choices."""

    institutions: list[FilterOption]
    instrument_types: list[FilterOption]
    analysis_types: list[FilterOption]
    microorganisms: list[FilterOption]
    researchers: list[FilterOption]


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
    address: str | None
    website: str | None
    contact_email: str | None
    status: str
    latitude: float | None
    longitude: float | None


class InstitutionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    description: str | None = None
    # The street address is looked up to place the institution on a map.
    # Explicit coordinates, when given, are used as-is and skip the lookup.
    address: str | None = Field(default=None, max_length=300)
    city: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=120)
    website: str | None = Field(default=None, max_length=500)
    contact_email: str | None = Field(default=None, max_length=320)
    status: Literal["draft", "active", "archived"] = "active"
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordinates_are_paired(self) -> "InstitutionCreate":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be given together")
        return self


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


# --- Detail views -----------------------------------------------------------
# Each entity that a search result can display has a detail endpoint. Related
# records are returned as small references so the UI can link deeper.


class InstitutionRef(ORMModel):
    id: int
    name: str
    city: str
    country: str
    status: str


class TypeRef(ORMModel):
    id: int
    name: str
    description: str | None


class InstrumentRef(BaseModel):
    id: int
    display_name: str | None
    type_name: str
    manufacturer: str | None
    model: str | None
    status: str
    usage: str | None = None


class AnalysisRef(BaseModel):
    id: int
    public_name: str | None
    type_name: str
    availability: str
    turnaround_days: int | None
    role: str | None = None
    usage: str | None = None
    institution: InstitutionRef | None = None


class TargetRef(ORMModel):
    id: int
    scientific_name: str
    common_name: str | None


class PersonRef(BaseModel):
    id: int
    full_name: str
    title: str | None
    status: str
    role: str | None = None
    institution: InstitutionRef | None = None


class InstitutionDetailView(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    address: str | None
    city: str
    country: str
    website: str | None
    contact_email: str | None
    status: str
    latitude: float | None
    longitude: float | None
    instruments: list[InstrumentRef]
    analyses: list[AnalysisRef]
    researchers: list[PersonRef]


class ResearcherDetailView(BaseModel):
    id: int
    full_name: str
    title: str | None
    email: str | None
    orcid: str | None
    expertise: str | None
    status: str
    institution: InstitutionRef
    analyses: list[AnalysisRef]


class InstrumentDetailView(BaseModel):
    id: int
    display_name: str | None
    manufacturer: str | None
    model: str | None
    status: str
    access_notes: str | None
    instrument_type: TypeRef
    institution: InstitutionRef
    analyses: list[AnalysisRef]


class AnalysisDetailView(BaseModel):
    id: int
    public_name: str | None
    description: str | None
    turnaround_days: int | None
    availability: str
    analysis_type: TypeRef
    institution: InstitutionRef
    instruments: list[InstrumentRef]
    targets: list[TargetRef]
    researchers: list[PersonRef]


class MicroorganismDetailView(BaseModel):
    id: int
    scientific_name: str
    common_name: str | None
    description: str | None
    analyses: list[AnalysisRef]


class InstrumentTypeDetailView(BaseModel):
    id: int
    name: str
    description: str | None
    instruments: list[InstrumentRef]
    institutions: list[InstitutionRef]


class AnalysisTypeDetailView(BaseModel):
    id: int
    name: str
    description: str | None
    analyses: list[AnalysisRef]
    institutions: list[InstitutionRef]
