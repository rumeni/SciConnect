import { describe, expect, it } from "vitest";
import { mergeSearchPage, nextPageQuery } from "./searchPagination";
import type { Filters } from "./SearchView";
import type { SearchResponse } from "./types";

const filters: Filters = {
  institution_ids: "",
  city: "Nis",
  instrument_type_ids: "",
  analysis_type_ids: "",
  microorganism_ids: "",
  researcher_ids: "",
};

function page(ids: number[], total: number, offset = 0): SearchResponse {
  return {
    items: ids.map((id) => ({
      institution: { id, name: `Institution ${id}`, slug: `institution-${id}`, city: "Nis", country: "Serbia" },
      matched_instruments: [],
      matched_analyses: [],
      matched_researchers: [],
    })),
    total,
    limit: 2,
    offset,
    institution_ids: [1, 2, 3, 4],
  };
}

describe("search pagination", () => {
  it("uses the applied filters rather than unsubmitted dropdown edits", () => {
    const shown = page([1, 2], 4);
    const draft: Filters = { ...filters, city: "Belgrade" };
    const request = nextPageQuery(filters, shown);

    expect(draft.city).toBe("Belgrade");
    expect(request).toEqual({ filters, offset: 2 });
    expect(request?.filters).not.toBe(filters);
    expect(filters.city).toBe("Nis");
  });

  it("appends the matching next page without dropping the first page", () => {
    const shown = page([1, 2], 4);
    const combined = mergeSearchPage(shown, page([3, 4], 4, 2), 2);
    expect(combined?.items.map((item) => item.institution.id)).toEqual([1, 2, 3, 4]);
    expect(nextPageQuery(filters, combined)).toBeNull();
  });

  it("replaces old results when a new search starts at offset zero", () => {
    const newPage = page([8], 1);
    expect(mergeSearchPage(page([1, 2], 4), newPage, 0)).toEqual(newPage);
  });

  it("does not append an out-of-sequence or orphaned page", () => {
    const previous = page([1, 2], 4);
    expect(mergeSearchPage(previous, page([4], 4, 3), 3)).toBe(previous);
    expect(mergeSearchPage(null, page([2], 4, 2), 2)).toBeNull();
    expect(nextPageQuery(filters, null)).toBeNull();
  });
});
