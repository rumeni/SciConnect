import { FormEvent, useEffect, useState } from "react";
import { api } from "./api";
import type { CatalogItem, Institution, Microorganism, SearchResponse } from "./types";

type Filters = {
  institution_ids: string;
  instrument_type_ids: string;
  analysis_type_ids: string;
  microorganism_ids: string;
};

const emptyFilters: Filters = {
  institution_ids: "",
  instrument_type_ids: "",
  analysis_type_ids: "",
  microorganism_ids: "",
};

export default function App() {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [instrumentTypes, setInstrumentTypes] = useState<CatalogItem[]>([]);
  const [analysisTypes, setAnalysisTypes] = useState<CatalogItem[]>([]);
  const [microorganisms, setMicroorganisms] = useState<Microorganism[]>([]);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const runSearch = async (nextFilters: Filters = filters) => {
    setLoading(true);
    setError("");
    try {
      setResults(await api.search(nextFilters));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    Promise.all([
      api.institutions(),
      api.instrumentTypes(),
      api.analysisTypes(),
      api.microorganisms(),
    ])
      .then(([institutionData, instrumentData, analysisData, microorganismData]) => {
        setInstitutions(institutionData);
        setInstrumentTypes(instrumentData);
        setAnalysisTypes(analysisData);
        setMicroorganisms(microorganismData);
        return runSearch(emptyFilters);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "API is unavailable");
        setLoading(false);
      });
  }, []);

  const updateFilter = (name: keyof Filters, value: string) => {
    setFilters((current) => ({ ...current, [name]: value }));
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void runSearch();
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
          Combine an institution, instrument, analysis and target organism. Results only
          include capabilities whose relationships are explicitly confirmed.
        </p>
      </header>

      <form className="filters" onSubmit={submit}>
        <Select label="Institution" value={filters.institution_ids} onChange={(value) => updateFilter("institution_ids", value)}>
          {institutions.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </Select>
        <Select label="Instrument" value={filters.instrument_type_ids} onChange={(value) => updateFilter("instrument_type_ids", value)}>
          {instrumentTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </Select>
        <Select label="Analysis" value={filters.analysis_type_ids} onChange={(value) => updateFilter("analysis_type_ids", value)}>
          {analysisTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </Select>
        <Select label="Target organism" value={filters.microorganism_ids} onChange={(value) => updateFilter("microorganism_ids", value)}>
          {microorganisms.map((item) => <option key={item.id} value={item.id}>{item.scientific_name}</option>)}
        </Select>
        <div className="actions">
          <button className="primary" type="submit">Search capabilities</button>
          <button className="secondary" type="button" onClick={clear}>Clear</button>
        </div>
      </form>

      <section className="results" aria-live="polite">
        <div className="results-heading">
          <h2>Matching institutions</h2>
          <span>{loading ? "Searching…" : `${results?.total ?? 0} results`}</span>
        </div>
        {error && <p className="error">{error}</p>}
        {!loading && !error && results?.items.length === 0 && (
          <p className="empty">No institution satisfies the selected combination.</p>
        )}
        <div className="result-grid">
          {results?.items.map((result) => (
            <article className="result-card" key={result.institution.id}>
              <div>
                <p className="location">{result.institution.city}, {result.institution.country}</p>
                <h3>{result.institution.name}</h3>
              </div>
              {result.matched_instruments.length > 0 && (
                <CapabilityGroup title="Matching instruments" items={result.matched_instruments.map((item) => item.display_name || item.type_name)} />
              )}
              {result.matched_analyses.map((analysis) => (
                <div className="offering" key={analysis.id}>
                  <div className="offering-title">
                    <strong>{analysis.public_name || analysis.type_name}</strong>
                    <span>{analysis.availability}</span>
                  </div>
                  {analysis.turnaround_days && <p>{analysis.turnaround_days} day turnaround</p>}
                  <CapabilityGroup title="Uses" items={analysis.instruments.map((item) => item.display_name || item.type_name)} />
                  <CapabilityGroup title="Targets" items={analysis.targets.map((item) => item.scientific_name)} />
                </div>
              ))}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function Select({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return (
    <label>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Any</option>
        {children}
      </select>
    </label>
  );
}

function CapabilityGroup({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="capability-group">
      <small>{title}</small>
      <div className="chips">{items.map((item) => <span key={item}>{item}</span>)}</div>
    </div>
  );
}

