import type { Filters } from "./SearchView";
import type { SearchResponse } from "./types";

/** Draft filter edits must not change the query that produced visible pages. */
export function nextPageQuery(
  applied: Filters,
  results: SearchResponse | null,
): { filters: Filters; offset: number } | null {
  if (!results || results.items.length >= results.total) return null;
  return { filters: { ...applied }, offset: results.items.length };
}

/** A new search replaces pages; an additional page may only extend its offset. */
export function mergeSearchPage(
  current: SearchResponse | null,
  page: SearchResponse,
  offset: number,
): SearchResponse | null {
  if (offset === 0) return page;
  if (!current || current.items.length !== offset) return current;
  return { ...page, items: [...current.items, ...page.items] };
}
