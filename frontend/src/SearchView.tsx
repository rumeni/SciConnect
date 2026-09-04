import { FormEvent, ReactNode } from "react";
import type {
  EntityRef,
  FilterOption,
  FilterOptions,
  ResearcherMatch,
  SearchResponse,
} from "./types";

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

/** A chip that opens the entity it names. */
function Chip({
  label,
  entity,
  onOpen,
}: {
  label: string;
  entity: EntityRef;
  onOpen: (ref: EntityRef) => void;
}) {
  return (
    <button type="button" className="chip" onClick={() => onOpen(entity)}>
      {label}
    </button>
  );
}

export function SearchView({
  options,
  filters,
  onFilterChange,
  onSearch,
  onClear,
  onOpen,
  results,
  loading,
  error,
}: {
  options: FilterOptions;
  filters: Filters;
  onFilterChange: (name: keyof Filters, value: string) => void;
  onSearch: () => void;
  onClear: () => void;
  onOpen: (ref: EntityRef) => void;
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
        <FilterSelect
          label="Institution"
          kind="institution"
          value={filters.institution_ids}
          onChange={(value) => onFilterChange("institution_ids", value)}
          onOpen={onOpen}
          options={options.institutions}
        />
        <FilterSelect
          label="Instrument"
          kind="instrument-type"
          value={filters.instrument_type_ids}
          onChange={(value) => onFilterChange("instrument_type_ids", value)}
          onOpen={onOpen}
          options={options.instrument_types}
        />
        <FilterSelect
          label="Analysis"
          kind="analysis-type"
          value={filters.analysis_type_ids}
          onChange={(value) => onFilterChange("analysis_type_ids", value)}
          onOpen={onOpen}
          options={options.analysis_types}
        />
        <FilterSelect
          label="Target organism"
          kind="microorganism"
          value={filters.microorganism_ids}
          onChange={(value) => onFilterChange("microorganism_ids", value)}
          onOpen={onOpen}
          options={options.microorganisms}
        />
        <FilterSelect
          label="Researcher"
          kind="researcher"
          value={filters.researcher_ids}
          onChange={(value) => onFilterChange("researcher_ids", value)}
          onOpen={onOpen}
          options={options.researchers}
        />
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
        <p className="results-hint">
          Each filter lists only values that still match the other choices. Select any name
          below to open its details.
        </p>
        <div className="result-grid">
          {results?.items.map((result) => (
            <article className="result-card" key={result.institution.id}>
              <div>
                <p className="location">
                  {result.institution.city}, {result.institution.country}
                </p>
                <h3>
                  <button
                    type="button"
                    className="title-button"
                    onClick={() => onOpen({ kind: "institution", id: result.institution.id })}
                  >
                    {result.institution.name}
                  </button>
                </h3>
              </div>
              {result.matched_instruments.length > 0 && (
                <Group title="Matching instruments">
                  {result.matched_instruments.map((item) => (
                    <Chip
                      key={item.id}
                      label={item.display_name || item.type_name}
                      entity={{ kind: "instrument", id: item.id }}
                      onOpen={onOpen}
                    />
                  ))}
                </Group>
              )}
              {result.matched_researchers.length > 0 && (
                <PeopleGroup
                  title="Researchers"
                  people={result.matched_researchers}
                  onOpen={onOpen}
                />
              )}
              {result.matched_analyses.map((analysis) => (
                <div className="offering" key={analysis.id}>
                  <div className="offering-title">
                    <button
                      type="button"
                      className="title-button strong"
                      onClick={() => onOpen({ kind: "analysis", id: analysis.id })}
                    >
                      {analysis.public_name || analysis.type_name}
                    </button>
                    <span>{analysis.availability}</span>
                  </div>
                  {analysis.turnaround_days && <p>{analysis.turnaround_days} day turnaround</p>}
                  {analysis.instruments.length > 0 && (
                    <Group title="Uses">
                      {analysis.instruments.map((item) => (
                        <Chip
                          key={item.id}
                          label={item.display_name || item.type_name}
                          entity={{ kind: "instrument", id: item.id }}
                          onOpen={onOpen}
                        />
                      ))}
                    </Group>
                  )}
                  {analysis.targets.length > 0 && (
                    <Group title="Targets">
                      {analysis.targets.map((item) => (
                        <Chip
                          key={item.id}
                          label={item.scientific_name}
                          entity={{ kind: "microorganism", id: item.id }}
                          onOpen={onOpen}
                        />
                      ))}
                    </Group>
                  )}
                  <PeopleGroup
                    title="Performed by"
                    people={analysis.researchers}
                    onOpen={onOpen}
                  />
                </div>
              ))}
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

/**
 * One filter. Its options are narrowed by the other selections, so every choice
 * still leads somewhere; the current selection can be opened in the detail panel.
 */
function FilterSelect({
  label,
  kind,
  value,
  onChange,
  onOpen,
  options,
}: {
  label: string;
  kind: EntityRef["kind"];
  value: string;
  onChange: (value: string) => void;
  onOpen: (ref: EntityRef) => void;
  options: FilterOption[];
}) {
  const empty = options.length === 0;
  return (
    <label>
      <span>{label}</span>
      <select
        value={value}
        disabled={empty}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{empty ? "None available" : "Any"}</option>
        {options.map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </select>
      {value && (
        <button
          type="button"
          className="link-button filter-detail"
          onClick={() => onOpen({ kind, id: Number(value) })}
        >
          View details
        </button>
      )}
    </label>
  );
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="capability-group">
      <small>{title}</small>
      <div className="chips">{children}</div>
    </div>
  );
}

function PeopleGroup({
  title,
  people,
  onOpen,
}: {
  title: string;
  people: ResearcherMatch[];
  onOpen: (ref: EntityRef) => void;
}) {
  if (people.length === 0) return null;
  return (
    <div className="capability-group">
      <small>{title}</small>
      <ul className="people">
        {people.map((person) => (
          <li key={person.id}>
            <button
              type="button"
              className="title-button strong"
              onClick={() => onOpen({ kind: "researcher", id: person.id })}
            >
              {person.full_name}
            </button>
            {person.role && <em className="role">{person.role}</em>}
            {person.title && <span className="person-title">{person.title}</span>}
            {person.expertise && <span className="person-expertise">{person.expertise}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
