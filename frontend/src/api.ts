import type { CatalogItem, Institution, Microorganism, SearchResponse } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  institutions: () => request<Institution[]>("/api/v1/catalog/institutions"),
  instrumentTypes: () => request<CatalogItem[]>("/api/v1/catalog/instrument-types"),
  analysisTypes: () => request<CatalogItem[]>("/api/v1/catalog/analysis-types"),
  microorganisms: () => request<Microorganism[]>("/api/v1/catalog/microorganisms"),
  search: (filters: Record<string, string>) => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) query.append(key, value);
    });
    return request<SearchResponse>(`/api/v1/capabilities/search?${query}`);
  },
};

