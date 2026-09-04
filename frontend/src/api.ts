import type {
  Catalogs,
  CatalogItem,
  CreatedInstitution,
  EntityDetail,
  EntityKind,
  EntityRef,
  FilterOptions,
  Institution,
  InstitutionAnalysis,
  InstitutionInstrument,
  Microorganism,
  Researcher,
  SearchResponse,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<T>;
}

/** FastAPI reports a plain string for domain errors and a list for validation errors. */
async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => `${(item.loc ?? []).slice(1).join(".")}: ${item.msg}`)
        .join("; ");
    }
  } catch {
    /* fall through to the status code */
  }
  return `Request failed (${response.status})`;
}

function asQuery(filters: Record<string, string>): URLSearchParams {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) query.append(key, value);
  });
  return query;
}

function post<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export const api = {
  institutions: () => request<Institution[]>("/api/v1/catalog/institutions"),
  instrumentTypes: () => request<CatalogItem[]>("/api/v1/catalog/instrument-types"),
  analysisTypes: () => request<CatalogItem[]>("/api/v1/catalog/analysis-types"),
  microorganisms: () => request<Microorganism[]>("/api/v1/catalog/microorganisms"),
  researchers: () => request<Researcher[]>("/api/v1/catalog/researchers"),
  institutionInstruments: () =>
    request<InstitutionInstrument[]>("/api/v1/catalog/institution-instruments"),
  institutionAnalyses: () =>
    request<InstitutionAnalysis[]>("/api/v1/catalog/institution-analyses"),

  search: (filters: Record<string, string>) =>
    request<SearchResponse>(`/api/v1/capabilities/search?${asQuery(filters)}`),

  filterOptions: (filters: Record<string, string>) =>
    request<FilterOptions>(`/api/v1/capabilities/filter-options?${asQuery(filters)}`),

  createInstitution: (payload: unknown) =>
    post<CreatedInstitution>("/api/v1/catalog/institutions", payload),
  createInstrumentType: (payload: unknown) =>
    post<CatalogItem>("/api/v1/catalog/instrument-types", payload),
  createAnalysisType: (payload: unknown) =>
    post<CatalogItem>("/api/v1/catalog/analysis-types", payload),
  createMicroorganism: (payload: unknown) =>
    post<Microorganism>("/api/v1/catalog/microorganisms", payload),
  createResearcher: (payload: unknown) =>
    post<Researcher>("/api/v1/catalog/researchers", payload),
  createInstitutionInstrument: (payload: unknown) =>
    post<InstitutionInstrument>("/api/v1/catalog/institution-instruments", payload),
  createInstitutionAnalysis: (payload: unknown) =>
    post<InstitutionAnalysis>("/api/v1/catalog/institution-analyses", payload),

  linkInstrument: (analysisId: number, payload: unknown) =>
    post<unknown>(`/api/v1/institution-analyses/${analysisId}/instruments`, payload),
  linkTarget: (analysisId: number, payload: unknown) =>
    post<unknown>(`/api/v1/institution-analyses/${analysisId}/targets`, payload),
  linkResearcher: (analysisId: number, payload: unknown) =>
    post<unknown>(`/api/v1/institution-analyses/${analysisId}/researchers`, payload),

  detail: async (ref: EntityRef): Promise<EntityDetail> => {
    const data = await request<never>(`/api/v1${DETAIL_PATHS[ref.kind]}/${ref.id}`);
    return { kind: ref.kind, data } as EntityDetail;
  },
};

const DETAIL_PATHS: Record<EntityKind, string> = {
  institution: "/catalog/institutions",
  researcher: "/catalog/researchers",
  instrument: "/catalog/institution-instruments",
  analysis: "/catalog/institution-analyses",
  microorganism: "/catalog/microorganisms",
  "instrument-type": "/catalog/instrument-types",
  "analysis-type": "/catalog/analysis-types",
};

export async function loadCatalogs(): Promise<Catalogs> {
  const [
    institutions,
    instrumentTypes,
    analysisTypes,
    microorganisms,
    researchers,
    institutionInstruments,
    institutionAnalyses,
  ] = await Promise.all([
    api.institutions(),
    api.instrumentTypes(),
    api.analysisTypes(),
    api.microorganisms(),
    api.researchers(),
    api.institutionInstruments(),
    api.institutionAnalyses(),
  ]);
  return {
    institutions,
    instrumentTypes,
    analysisTypes,
    microorganisms,
    researchers,
    institutionInstruments,
    institutionAnalyses,
  };
}
