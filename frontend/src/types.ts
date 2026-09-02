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

export type InstrumentMatch = {
  id: number;
  instrument_type_id: number;
  type_name: string;
  display_name: string | null;
  manufacturer: string | null;
  model: string | null;
  status: string;
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
};

export type CapabilityResult = {
  institution: Institution;
  matched_instruments: InstrumentMatch[];
  matched_analyses: AnalysisMatch[];
};

export type SearchResponse = {
  items: CapabilityResult[];
  total: number;
  limit: number;
  offset: number;
};

