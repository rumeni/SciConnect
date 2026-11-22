import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactElement, ReactNode } from "react";
import type { Filters } from "./SearchView";
import type { Catalogs, FilterOptions, SearchResponse } from "./types";

// Exercise Workspace's actual callback wiring without bringing a DOM test runner
// into the project. Child views are inert; hooks expose the parent state/actions.
const hookState = vi.hoisted(() => ({
  index: 0,
  values: [] as unknown[],
  effects: [] as Array<() => void>,
}));

vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>();
  return {
    ...actual,
    useState: (initial: unknown) => {
      const index = hookState.index++;
      if (index >= hookState.values.length) {
        hookState.values[index] = typeof initial === "function"
          ? (initial as () => unknown)()
          : initial;
      }
      const set = (next: unknown) => {
        const old = hookState.values[index];
        hookState.values[index] = typeof next === "function"
          ? (next as (value: unknown) => unknown)(old)
          : next;
      };
      return [hookState.values[index], set];
    },
    useRef: (initial: unknown) => ({ current: initial }),
    useEffect: (effect: () => void) => { hookState.effects.push(effect); },
    useMemo: (calculate: () => unknown) => calculate(),
    useCallback: (callback: unknown) => callback,
  };
});

vi.mock("./api", () => ({
  api: {
    search: vi.fn(),
    filterOptions: vi.fn(),
    mapInstitutions: vi.fn(),
  },
  loadCatalogs: vi.fn(),
}));
vi.mock("./i18n", () => ({ useT: () => (key: string) => key }));
vi.mock("./SearchView", () => ({
  emptyFilters: {
    institution_ids: "",
    city: "",
    instrument_type_ids: "",
    analysis_type_ids: "",
    microorganism_ids: "",
    researcher_ids: "",
  },
  SearchView: () => null,
}));
vi.mock("./viewerLocation", () => ({
  readStoredLocation: () => null,
  forgetLocation: vi.fn(),
  hasBeenAsked: () => true,
  rememberAsked: vi.fn(),
  storeLocation: vi.fn(),
}));
vi.mock("./LanguageSwitch", () => ({ LanguageSwitch: () => null }));
vi.mock("./Logo", () => ({ Brand: () => null }));
vi.mock("./DetailPanel", () => ({ DetailPanel: () => null }));
vi.mock("./EntitySearch", () => ({ EntitySearch: () => null }));
vi.mock("./LocationPrompt", () => ({ LocationPrompt: () => null }));
vi.mock("./ManageView", () => ({ ManageView: () => null }));
vi.mock("./NearbyView", () => ({ NearbyView: () => null }));

import { Workspace } from "./Workspace";
import { api, loadCatalogs } from "./api";
import { SearchView } from "./SearchView";

const emptyFilters: Filters = {
  institution_ids: "",
  city: "",
  instrument_type_ids: "",
  analysis_type_ids: "",
  microorganism_ids: "",
  researcher_ids: "",
};
const emptyCatalogs: Catalogs = {
  institutions: [], instrumentTypes: [], analysisTypes: [],
  microorganisms: [], researchers: [], institutionInstruments: [], institutionAnalyses: [],
};
const noOptions: FilterOptions = {
  institutions: [], instrument_types: [], analysis_types: [],
  microorganisms: [], researchers: [], cities: [],
};
function page(ids: number[], total = ids.length, offset = 0): SearchResponse {
  return {
    items: ids.map((id) => ({
      institution: { id, name: `Institute ${id}`, slug: `i-${id}`, city: "Nis", country: "Serbia" },
      matched_instruments: [], matched_analyses: [], matched_researchers: [],
    })),
    offset, total, limit: 20, institution_ids: ids,
  };
}

function findSearchView(node: ReactNode): ReactElement<Parameters<typeof SearchView>[0]> {
  if (Array.isArray(node)) {
    for (const part of node) {
      try { return findSearchView(part); } catch { /* search remaining nodes */ }
    }
  } else if (node !== null && typeof node === "object" && "type" in node && "props" in node) {
    const element = node as ReactElement<{ children?: ReactNode }>;
    if (element.type === SearchView) {
      return element as ReactElement<Parameters<typeof SearchView>[0]>;
    }
    return findSearchView(element.props.children);
  }
  throw new Error("Workspace did not render SearchView");
}

function workspace(role: "guest" | "admin" = "guest") {
  hookState.index = 0;
  const tree = Workspace({ role, onSignIn: () => {}, onLeave: () => {} });
  return findSearchView(tree).props;
}

function seedState({
  draft = "Belgrade", applied = "Nis", results = page(Array.from({ length: 20 }, (_, i) => i + 1), 40),
}: {
  draft?: string;
  applied?: string;
  results?: SearchResponse;
} = {}) {
  hookState.index = 0;
  hookState.effects = [];
  // Workspace's 14 useState calls, in source order.
  hookState.values = [
    "search",
    emptyCatalogs,
    { ...emptyFilters, city: draft },
    noOptions,
    results,
    { ...emptyFilters, city: applied },
    false,
    "",
    [],
    [],
    null,
    false,
    0,
    false, // refreshing the catalog
  ];
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}
async function flush() {
  for (let i = 0; i < 5; i++) await Promise.resolve();
}

beforeEach(() => {
  vi.clearAllMocks();
  seedState();
  vi.mocked(api.search).mockResolvedValue(page([99], 1));
  vi.mocked(api.filterOptions).mockResolvedValue(noOptions);
  vi.mocked(api.mapInstitutions).mockResolvedValue([]);
  vi.mocked(loadCatalogs).mockResolvedValue(emptyCatalogs);
});

describe("Workspace interactions", () => {
  it("Load more actually submits applied filters, never unsubmitted dropdown changes", () => {
    const props = workspace();
    props.onLoadMore();
    expect(api.search).toHaveBeenCalledExactlyOnceWith({ ...emptyFilters, city: "Nis" }, 20);
  });

  it("does not let a slow initial refresh override a newer submitted search", async () => {
    const catalogs = deferred<Catalogs>();
    vi.mocked(loadCatalogs).mockReturnValueOnce(catalogs.promise);
    const props = workspace();
    hookState.effects[1](); // initial refresh
    props.onSearch(); // the visitor submits the edited city while refresh is loading
    expect(api.search).toHaveBeenCalledExactlyOnceWith({ ...emptyFilters, city: "Belgrade" }, 0);
    catalogs.resolve(emptyCatalogs);
    await flush();
    expect(api.search).toHaveBeenCalledTimes(1);
  });

  it("blocks Load more during post-write refresh, then replaces page one", async () => {
    const catalogs = deferred<Catalogs>();
    vi.mocked(loadCatalogs).mockReturnValueOnce(catalogs.promise);
    const props = workspace("admin");
    hookState.effects[1](); // refresh begins while old results are shown
    expect(hookState.values[13]).toBe(true);
    props.onLoadMore(); // a click racing the disabled-button render
    expect(api.search).not.toHaveBeenCalled();
    catalogs.resolve(emptyCatalogs);
    await flush();
    expect(api.search).toHaveBeenCalledExactlyOnceWith({ ...emptyFilters, city: "Nis" }, 0);
    expect(hookState.values[13]).toBe(false);
  });

  it("keeps paging blocked during overlapping refreshes and applies only the newest snapshot", async () => {
    const first = deferred<Catalogs>();
    const second = deferred<Catalogs>();
    vi.mocked(loadCatalogs)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const props = workspace("admin");

    hookState.effects[1](); // write A
    hookState.effects[1](); // write B, before A finishes
    first.resolve(emptyCatalogs);
    await flush();

    // A must neither re-enable pagination nor start an obsolete offset-zero search.
    expect(hookState.values[13]).toBe(true);
    expect(api.search).not.toHaveBeenCalled();
    props.onLoadMore();
    expect(api.search).not.toHaveBeenCalled();

    second.resolve(emptyCatalogs);
    await flush();
    expect(api.search).toHaveBeenCalledExactlyOnceWith({ ...emptyFilters, city: "Nis" }, 0);
    expect(hookState.values[13]).toBe(false);
  });

  it("does not page stale data when the newer refresh fails during an older search", async () => {
    const first = deferred<Catalogs>();
    const second = deferred<Catalogs>();
    const searching = deferred<SearchResponse>();
    vi.mocked(loadCatalogs)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    vi.mocked(api.search).mockReturnValueOnce(searching.promise);
    const props = workspace("admin");

    hookState.effects[1](); // refresh A begins
    first.resolve(emptyCatalogs);
    await flush();
    expect(api.search).toHaveBeenCalledExactlyOnceWith({ ...emptyFilters, city: "Nis" }, 0);

    // Refresh A has started an offset-zero search but its response is pending.
    hookState.effects[1](); // refresh B begins
    second.reject(new Error("Catalog B failed"));
    await flush();

    expect(hookState.values[7]).toBe("Catalog B failed");
    expect(hookState.values[6]).toBe(true); // A still owns the search loading flag
    props.onLoadMore(); // B's failed refresh must not reopen paging
    expect(api.search).toHaveBeenCalledTimes(1);

    searching.resolve(page([99], 1));
    await flush();
    expect(hookState.values[6]).toBe(false);
  });

  it("reports catalog errors even when a newer search was submitted", async () => {
    const catalogs = deferred<Catalogs>();
    vi.mocked(loadCatalogs).mockReturnValueOnce(catalogs.promise);
    const props = workspace();
    hookState.effects[1]();
    props.onSearch();
    catalogs.reject(new Error("Catalog unavailable"));
    await flush();

    expect(hookState.values[7]).toBe("Catalog unavailable");
    expect(hookState.values[13]).toBe(false);
  });

  it("loads the privileged institution catalog only in an admin workspace", async () => {
    workspace("admin");
    hookState.effects[1]();
    await flush();
    expect(loadCatalogs).toHaveBeenCalledWith(true);

    vi.clearAllMocks();
    seedState();
    workspace("guest");
    hookState.effects[1]();
    await flush();
    expect(loadCatalogs).toHaveBeenCalledWith(false);
  });
});
