import type {
  Catalogs,
  CatalogItem,
  CreatedInstitution,
  DeleteAck,
  EntityDetail,
  EntityKind,
  EntityRef,
  EntitySearchResponse,
  FilterOptions,
  GeocodeResult,
  Institution,
  InstitutionMapPoint,
  InstitutionAnalysis,
  InstitutionInstrument,
  Microorganism,
  Researcher,
  SearchResponse,
} from "./types";

declare global {
  interface Window {
    __SCICONNECT__?: { apiUrl?: string };
  }
}

/**
 * Where the API lives. The runtime value written by the container wins, so a
 * deployed image can be pointed at a different API without being rebuilt; the
 * build-time value serves local development.
 */
const API_URL =
  window.__SCICONNECT__?.apiUrl || import.meta.env.VITE_API_URL || "http://localhost:8000";

/** An error that kept the status, so callers can tell a refusal from a failure. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
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

function remove<T = unknown>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
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

  unlinkInstrument: (analysisId: number, instrumentId: number) =>
    remove(`/api/v1/institution-analyses/${analysisId}/instruments/${instrumentId}`),
  unlinkTarget: (analysisId: number, microorganismId: number) =>
    remove(`/api/v1/institution-analyses/${analysisId}/targets/${microorganismId}`),
  unlinkResearcher: (analysisId: number, researcherId: number) =>
    remove(`/api/v1/institution-analyses/${analysisId}/researchers/${researcherId}`),

  /** Delete a record. Institutions need `cascade` to take their contents too. */
  removeEntity: (ref: EntityRef, cascade = false) =>
    remove<DeleteAck>(
      `/api/v1${DETAIL_PATHS[ref.kind]}/${ref.id}${cascade ? "?cascade=true" : ""}`,
    ),

  findEntities: (query: string) =>
    request<EntitySearchResponse>(`/api/v1/search?q=${encodeURIComponent(query)}`),

  mapInstitutions: () => request<InstitutionMapPoint[]>("/api/v1/map/institutions"),

  geocode: (query: string) =>
    request<GeocodeResult>(`/api/v1/geocode?q=${encodeURIComponent(query)}`),

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
