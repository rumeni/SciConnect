import { useCallback, useEffect, useState } from "react";
import { api, loadCatalogs } from "./api";
import { ManageView } from "./ManageView";
import { emptyFilters, SearchView, type Filters } from "./SearchView";
import type { Catalogs, SearchResponse } from "./types";

const emptyCatalogs: Catalogs = {
  institutions: [],
  instrumentTypes: [],
  analysisTypes: [],
  microorganisms: [],
  researchers: [],
  institutionInstruments: [],
  institutionAnalyses: [],
};

type View = "search" | "contribute";

export default function App() {
  const [view, setView] = useState<View>("search");
  const [catalogs, setCatalogs] = useState<Catalogs>(emptyCatalogs);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const runSearch = useCallback(async (nextFilters: Filters) => {
    setLoading(true);
    setError("");
    try {
      setResults(await api.search(nextFilters));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      setCatalogs(await loadCatalogs());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "API is unavailable");
      setLoading(false);
      return;
    }
    await runSearch(filters);
  }, [filters, runSearch]);

  useEffect(() => {
    void refresh();
    // The initial load must not re-run when the filters change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updateFilter = (name: keyof Filters, value: string) => {
    setFilters((current) => ({ ...current, [name]: value }));
  };

  const clear = () => {
    setFilters(emptyFilters);
    void runSearch(emptyFilters);
  };

  return (
    <main>
      <header className="hero">
        <p className="eyebrow">Scientific capability discovery</p>
        <h1>Find the institution that can do the work.</h1>
        <p className="intro">
          Combine an institution, instrument, analysis, target organism and researcher. Results
          only include capabilities whose relationships are explicitly confirmed.
        </p>
      </header>

      <nav className="tabs" aria-label="Views">
        <button
          type="button"
          className={view === "search" ? "tab active" : "tab"}
          onClick={() => setView("search")}
        >
          Search
        </button>
        <button
          type="button"
          className={view === "contribute" ? "tab active" : "tab"}
          onClick={() => setView("contribute")}
        >
          Add &amp; connect
        </button>
      </nav>

      {view === "search" ? (
        <SearchView
          catalogs={catalogs}
          filters={filters}
          onFilterChange={updateFilter}
          onSearch={() => void runSearch(filters)}
          onClear={clear}
          results={results}
          loading={loading}
          error={error}
        />
      ) : (
        <ManageView catalogs={catalogs} onChanged={() => void refresh()} />
      )}
    </main>
  );
}
