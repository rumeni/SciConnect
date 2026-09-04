import { FormEvent } from "react";
import { Select } from "./form";
import type { Catalogs, ResearcherMatch, SearchResponse } from "./types";

export type Filters = {
  institution_ids: string;
  instrument_type_ids: string;
  analysis_type_ids: string;
  microorganism_ids: string;
  researcher_ids: string;
};

export const emptyFilters: Filters = {
  institution_ids: "",
  instrument_type_ids: "",
  analysis_type_ids: "",
  microorganism_ids: "",
  researcher_ids: "",
};

export function SearchView({
  catalogs,
  filters,
  onFilterChange,
  onSearch,
  onClear,
  results,
  loading,
  error,
}: {
  catalogs: Catalogs;
  filters: Filters;
  onFilterChange: (name: keyof Filters, value: string) => void;
  onSearch: () => void;
  onClear: () => void;
  results: SearchResponse | null;
  loading: boolean;
  error: string;
}) {
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSearch();
  };

  return (
    <>
      <form className="filters" onSubmit={submit}>
        <Select
          label="Institution"
          value={filters.institution_ids}
          onChange={(value) => onFilterChange("institution_ids", value)}
        >
          {catalogs.institutions.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </Select>
        <Select
          label="Instrument"
          value={filters.instrument_type_ids}
          onChange={(value) => onFilterChange("instrument_type_ids", value)}
        >
          {catalogs.instrumentTypes.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </Select>
        <Select
          label="Analysis"
          value={filters.analysis_type_ids}
          onChange={(value) => onFilterChange("analysis_type_ids", value)}
        >
          {catalogs.analysisTypes.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </Select>
        <Select
          label="Target organism"
          value={filters.microorganism_ids}
          onChange={(value) => onFilterChange("microorganism_ids", value)}
        >
          {catalogs.microorganisms.map((item) => (
            <option key={item.id} value={item.id}>
              {item.scientific_name}
            </option>
          ))}
        </Select>
        <Select
          label="Researcher"
          value={filters.researcher_ids}
          onChange={(value) => onFilterChange("researcher_ids", value)}
        >
          {catalogs.researchers.map((item) => (
            <option key={item.id} value={item.id}>
              {item.full_name}
            </option>
          ))}
        </Select>
        <div className="actions">
          <button className="primary" type="submit">
            Search capabilities
          </button>
          <button className="secondary" type="button" onClick={onClear}>
            Clear
          </button>
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
                <p className="location">
                  {result.institution.city}, {result.institution.country}
                </p>
                <h3>{result.institution.name}</h3>
              </div>
              {result.matched_instruments.length > 0 && (
                <CapabilityGroup
                  title="Matching instruments"
                  items={result.matched_instruments.map(
                    (item) => item.display_name || item.type_name,
                  )}
                />
              )}
              {result.matched_researchers.length > 0 && (
                <PeopleGroup title="Researchers" people={result.matched_researchers} />
              )}
              {result.matched_analyses.map((analysis) => (
                <div className="offering" key={analysis.id}>
                  <div className="offering-title">
                    <strong>{analysis.public_name || analysis.type_name}</strong>
                    <span>{analysis.availability}</span>
                  </div>
                  {analysis.turnaround_days && <p>{analysis.turnaround_days} day turnaround</p>}
                  <CapabilityGroup
                    title="Uses"
                    items={analysis.instruments.map(
                      (item) => item.display_name || item.type_name,
                    )}
                  />
                  <CapabilityGroup
                    title="Targets"
                    items={analysis.targets.map((item) => item.scientific_name)}
                  />
                  <PeopleGroup title="Performed by" people={analysis.researchers} />
                </div>
              ))}
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

function CapabilityGroup({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="capability-group">
      <small>{title}</small>
      <div className="chips">
        {items.map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
    </div>
  );
}

function PeopleGroup({ title, people }: { title: string; people: ResearcherMatch[] }) {
  if (people.length === 0) return null;
  return (
    <div className="capability-group">
      <small>{title}</small>
      <ul className="people">
        {people.map((person) => (
          <li key={person.id}>
            <strong>{person.full_name}</strong>
            {person.role && <em className="role">{person.role}</em>}
            {person.title && <span className="person-title">{person.title}</span>}
            {person.expertise && <span className="person-expertise">{person.expertise}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
