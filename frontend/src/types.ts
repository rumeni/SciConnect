export type CatalogItem = {
  id: number;
  name: string;
};

export type Institution = {
  id: number;
  name: string;
  slug: string;
  city: string;
  country: string;
};

/** What the create endpoint answers: the summary plus the derived position. */
export type CreatedInstitution = Institution & {
  description: string | null;
  address: string | null;
  website: string | null;
  contact_email: string | null;
  status: string;
  latitude: number | null;
  longitude: number | null;
};

export type Microorganism = {
  id: number;
  scientific_name: string;
  common_name: string | null;
};

export type Researcher = {
  id: number;
  institution_id: number;
  full_name: string;
  title: string | null;
  email: string | null;
  orcid: string | null;
  expertise: string | null;
  status: string;
};

export type InstitutionInstrument = {
  id: number;
  institution_id: number;
  instrument_type_id: number;
  display_name: string | null;
  manufacturer: string | null;
  model: string | null;
  status: string;
};

export type InstitutionAnalysis = {
  id: number;
  institution_id: number;
  analysis_type_id: number;
  public_name: string | null;
  description: string | null;
  turnaround_days: number | null;
  availability: string;
};

export type InstrumentMatch = {
  id: number;
  instrument_type_id: number;
  type_name: string;
  display_name: string | null;
  manufacturer: string | null;
  model: string | null;
  status: string;
};

export type ResearcherMatch = {
  id: number;
  full_name: string;
  title: string | null;
  email: string | null;
  orcid: string | null;
  expertise: string | null;
  status: string;
  role: string | null;
};

export type AnalysisMatch = {
  id: number;
  analysis_type_id: number;
  type_name: string;
  public_name: string | null;
  availability: string;
  turnaround_days: number | null;
  instruments: InstrumentMatch[];
  targets: { id: number; scientific_name: string }[];
  researchers: ResearcherMatch[];
};

export type CapabilityResult = {
  institution: Institution;
  matched_instruments: InstrumentMatch[];
  matched_analyses: AnalysisMatch[];
  matched_researchers: ResearcherMatch[];
};

export type SearchResponse = {
  items: CapabilityResult[];
  total: number;
  limit: number;
  offset: number;
};

export type FilterOption = {
  id: number;
  label: string;
};

/** The values each filter can still offer, given the other current choices. */
export type FilterOptions = {
  institutions: FilterOption[];
  instrument_types: FilterOption[];
  analysis_types: FilterOption[];
  microorganisms: FilterOption[];
  researchers: FilterOption[];
};

export type Catalogs = {
  institutions: Institution[];
  instrumentTypes: CatalogItem[];
  analysisTypes: CatalogItem[];
  microorganisms: Microorganism[];
  researchers: Researcher[];
  institutionInstruments: InstitutionInstrument[];
  institutionAnalyses: InstitutionAnalysis[];
};

/** Every entity kind that can be opened in the detail panel. */
export type EntityKind =
  | "institution"
  | "researcher"
  | "instrument"
  | "analysis"
  | "microorganism"
  | "instrument-type"
  | "analysis-type";

export type EntityRef = {
  kind: EntityKind;
  id: number;
};

export type InstitutionRef = {
  id: number;
  name: string;
  city: string;
  country: string;
  status: string;
};

export type TypeRef = {
  id: number;
  name: string;
  description: string | null;
};

export type InstrumentRef = {
  id: number;
  display_name: string | null;
  type_name: string;
  manufacturer: string | null;
  model: string | null;
  status: string;
  usage: string | null;
};

export type AnalysisRef = {
  id: number;
  public_name: string | null;
  type_name: string;
  availability: string;
  turnaround_days: number | null;
  role: string | null;
  usage: string | null;
  institution: InstitutionRef | null;
};

export type TargetRef = {
  id: number;
  scientific_name: string;
  common_name: string | null;
};

export type PersonRef = {
  id: number;
  full_name: string;
  title: string | null;
  status: string;
  role: string | null;
  institution: InstitutionRef | null;
};

export type InstitutionDetailView = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  address: string | null;
  city: string;
  country: string;
  website: string | null;
  contact_email: string | null;
  status: string;
  latitude: number | null;
  longitude: number | null;
  instruments: InstrumentRef[];
  analyses: AnalysisRef[];
  researchers: PersonRef[];
};

export type ResearcherDetailView = {
  id: number;
  full_name: string;
  title: string | null;
  email: string | null;
  orcid: string | null;
  expertise: string | null;
  status: string;
  institution: InstitutionRef;
  analyses: AnalysisRef[];
};

export type InstrumentDetailView = {
  id: number;
  display_name: string | null;
  manufacturer: string | null;
  model: string | null;
  status: string;
  access_notes: string | null;
  instrument_type: TypeRef;
  institution: InstitutionRef;
  analyses: AnalysisRef[];
};

export type AnalysisDetailView = {
  id: number;
  public_name: string | null;
  description: string | null;
  turnaround_days: number | null;
  availability: string;
  analysis_type: TypeRef;
  institution: InstitutionRef;
  instruments: InstrumentRef[];
  targets: TargetRef[];
  researchers: PersonRef[];
};

export type MicroorganismDetailView = {
  id: number;
  scientific_name: string;
  common_name: string | null;
  description: string | null;
  analyses: AnalysisRef[];
};

export type InstrumentTypeDetailView = {
  id: number;
  name: string;
  description: string | null;
  instruments: InstrumentRef[];
  institutions: InstitutionRef[];
};

export type AnalysisTypeDetailView = {
  id: number;
  name: string;
  description: string | null;
  analyses: AnalysisRef[];
  institutions: InstitutionRef[];
};

export type EntityDetail =
  | { kind: "institution"; data: InstitutionDetailView }
  | { kind: "researcher"; data: ResearcherDetailView }
  | { kind: "instrument"; data: InstrumentDetailView }
  | { kind: "analysis"; data: AnalysisDetailView }
  | { kind: "microorganism"; data: MicroorganismDetailView }
  | { kind: "instrument-type"; data: InstrumentTypeDetailView }
  | { kind: "analysis-type"; data: AnalysisTypeDetailView };
