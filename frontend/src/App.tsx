import { useCallback, useEffect, useState } from "react";
import { api, loadCatalogs } from "./api";
import { Brand } from "./Logo";
import { DetailPanel } from "./DetailPanel";
import { LocationPrompt } from "./LocationPrompt";
import { ManageView } from "./ManageView";
import { NearbyView } from "./NearbyView";
import { emptyFilters, SearchView, type Filters } from "./SearchView";
import {
  forgetLocation,
  hasBeenAsked,
  readStoredLocation,
  rememberAsked,
  storeLocation,
} from "./viewerLocation";
import type {
  Catalogs,
  EntityRef,
  FilterOptions,
  InstitutionMapPoint,
  SearchResponse,
  ViewerLocation,
} from "./types";

const noOptions: FilterOptions = {
  institutions: [],
  instrument_types: [],
  analysis_types: [],
  microorganisms: [],
  researchers: [],
};

const emptyCatalogs: Catalogs = {
  institutions: [],
  instrumentTypes: [],
  analysisTypes: [],
  microorganisms: [],
  researchers: [],
  institutionInstruments: [],
  institutionAnalyses: [],
};

type View = "search" | "nearby" | "contribute";

export default function App() {
  const [view, setView] = useState<View>("search");
  const [catalogs, setCatalogs] = useState<Catalogs>(emptyCatalogs);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [options, setOptions] = useState<FilterOptions>(noOptions);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  // Opening a related record pushes onto the stack, so "Back" returns to the
  // record it was reached from.
  const [detailStack, setDetailStack] = useState<EntityRef[]>([]);
  const [mapPoints, setMapPoints] = useState<InstitutionMapPoint[]>([]);
  const [location, setLocation] = useState<ViewerLocation | null>(readStoredLocation);
  const [askingLocation, setAskingLocation] = useState(false);

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

  // Each filter offers only values that still lead somewhere, so the options
  // are recomputed whenever a selection changes.
  useEffect(() => {
    let active = true;
    api
      .filterOptions(filters)
      .then((next) => {
        if (active) setOptions(next);
      })
      .catch(() => {
        /* Leave the previous options in place; the search reports failures. */
      });
    return () => {
      active = false;
    };
  }, [
    filters.institution_ids,
    filters.instrument_type_ids,
    filters.analysis_type_ids,
    filters.microorganism_ids,
    filters.researcher_ids,
  ]);

  const refresh = useCallback(async () => {
    try {
      const [loaded, points] = await Promise.all([loadCatalogs(), api.mapInstitutions()]);
      setCatalogs(loaded);
      setMapPoints(points);
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

  // Offered once per browser, and never on its own initiative afterwards.
  useEffect(() => {
    if (!readStoredLocation() && !hasBeenAsked()) setAskingLocation(true);
  }, []);

  const acceptLocation = (shared: ViewerLocation) => {
    setLocation(shared);
    storeLocation(shared);
    rememberAsked();
    setAskingLocation(false);
    setView("nearby");
  };

  const declineLocation = () => {
    rememberAsked();
    setAskingLocation(false);
  };

  const forget = () => {
    setLocation(null);
    forgetLocation();
  };

  const openDetail = (ref: EntityRef) => setDetailStack((current) => [...current, ref]);
  const closeDetail = useCallback(() => setDetailStack([]), []);
  const backDetail = () => setDetailStack((current) => current.slice(0, -1));

  return (
    <main>
      <Brand />

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
          className={view === "nearby" ? "tab active" : "tab"}
          onClick={() => setView("nearby")}
        >
          Near me
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
          options={options}
          filters={filters}
          onFilterChange={updateFilter}
          onSearch={() => void runSearch(filters)}
          onClear={clear}
          onOpen={openDetail}
          results={results}
          loading={loading}
          error={error}
        />
      ) : view === "nearby" ? (
        <NearbyView
          location={location}
          institutions={mapPoints}
          onOpen={openDetail}
          onAsk={() => setAskingLocation(true)}
          onForget={forget}
        />
      ) : (
        <ManageView catalogs={catalogs} onChanged={() => void refresh()} />
      )}

      {askingLocation && (
        <LocationPrompt onShare={acceptLocation} onDismiss={declineLocation} />
      )}

      <DetailPanel
        stack={detailStack}
        onOpen={openDetail}
        onBack={backDetail}
        onClose={closeDetail}
      />
    </main>
  );
}
