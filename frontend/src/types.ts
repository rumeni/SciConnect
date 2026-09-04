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

export type Catalogs = {
  institutions: Institution[];
  instrumentTypes: CatalogItem[];
  analysisTypes: CatalogItem[];
  microorganisms: Microorganism[];
  researchers: Researcher[];
  institutionInstruments: InstitutionInstrument[];
  institutionAnalyses: InstitutionAnalysis[];
};
