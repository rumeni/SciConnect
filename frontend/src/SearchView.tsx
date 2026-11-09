import {
  FormEvent,
  KeyboardEvent,
  ReactNode,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { useT } from "./i18n";
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
  onLoadMore,
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
  onLoadMore: () => void;
  onClear: () => void;
  onOpen: (ref: EntityRef) => void;
  results: SearchResponse | null;
  loading: boolean;
  error: string;
}) {
  const t = useT();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSearch();
  };

  return (
    <>
      <form className="filters" onSubmit={submit}>
        <FilterSelect
          label={t("search.institution")}
          placeholder={t("search.placeholder.institution")}
          kind="institution"
          value={filters.institution_ids}
          onChange={(value) => onFilterChange("institution_ids", value)}
          onOpen={onOpen}
          options={options.institutions}
        />
        <FilterSelect
          label={t("search.instrument")}
          placeholder={t("search.placeholder.instrument")}
          kind="instrument-type"
          value={filters.instrument_type_ids}
          onChange={(value) => onFilterChange("instrument_type_ids", value)}
          onOpen={onOpen}
          options={options.instrument_types}
        />
        <FilterSelect
          label={t("search.analysis")}
          placeholder={t("search.placeholder.analysis")}
          kind="analysis-type"
          value={filters.analysis_type_ids}
          onChange={(value) => onFilterChange("analysis_type_ids", value)}
          onOpen={onOpen}
          options={options.analysis_types}
        />
        <FilterSelect
          label={t("search.organism")}
          placeholder={t("search.placeholder.organism")}
          kind="microorganism"
          value={filters.microorganism_ids}
          onChange={(value) => onFilterChange("microorganism_ids", value)}
          onOpen={onOpen}
          options={options.microorganisms}
        />
        <FilterSelect
          label={t("search.researcher")}
          placeholder={t("search.placeholder.researcher")}
          kind="researcher"
          value={filters.researcher_ids}
          onChange={(value) => onFilterChange("researcher_ids", value)}
          onOpen={onOpen}
          options={options.researchers}
        />
        <div className="actions">
          <button className="primary" type="submit">
            {t("search.submit")}
          </button>
          <button className="secondary" type="button" onClick={onClear}>
            {t("search.clear")}
          </button>
        </div>
      </form>

      <section className="results" aria-live="polite">
        <div className="results-heading">
          <h2>{t("search.results")}</h2>
          <span>
            {loading
              ? t("search.searching")
              : t("search.count", { count: results?.total ?? 0 })}
          </span>
        </div>
        {error && <p className="error">{error}</p>}
        {!loading && !error && results?.items.length === 0 && (
          <p className="empty">{t("search.none")}</p>
        )}
        <p className="results-hint">{t("search.hint")}</p>
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
                <Group title={t("search.matchedInstruments")}>
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
                  title={t("search.researchers")}
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
                  {analysis.turnaround_days && (
                    <p>{t("search.turnaround", { days: analysis.turnaround_days })}</p>
                  )}
                  {analysis.instruments.length > 0 && (
                    <Group title={t("search.uses")}>
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
                    <Group title={t("search.targets")}>
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
                    title={t("search.performedBy")}
                    people={analysis.researchers}
                    onOpen={onOpen}
                  />
                </div>
              ))}
            </article>
          ))}
        </div>
        {results && results.items.length < results.total && (
          <div className="load-more">
            <button
              type="button"
              className="secondary"
              disabled={loading}
              onClick={onLoadMore}
            >
              {loading
                ? t("common.loading")
                : t("search.showMore", {
                    shown: results.items.length,
                    total: results.total,
                  })}
            </button>
          </div>
        )}
      </section>
    </>
  );
}

/** Lower-cases and strips diacritics, so "sabac" finds "Šabac". */
function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase();
}

/** Every option matching the query, ranked: whole-label prefixes first, then word prefixes, then anywhere. */
function suggest(options: FilterOption[], query: string): FilterOption[] {
  const q = fold(query.trim());
  if (!q) return options;
  const ranked: { item: FilterOption; rank: number }[] = [];
  for (const item of options) {
    const label = fold(item.label);
    const at = label.indexOf(q);
    if (at < 0) continue;
    const rank = at === 0 ? 0 : label.split(/[\s,.()\-/]+/).some((w) => w.startsWith(q)) ? 1 : 2;
    ranked.push({ item, rank });
  }
  ranked.sort((a, b) => a.rank - b.rank);
  return ranked.map((r) => r.item);
}

/** The label with the typed part in bold, as in a map search box. */
function Highlight({ label, query }: { label: string; query: string }) {
  const q = fold(query.trim());
  // fold() keeps one character per character, so indexes line up with the label.
  const folded = fold(label);
  const at = q ? folded.indexOf(q) : -1;
  if (at < 0 || folded.length !== label.length) return <>{label}</>;
  return (
    <>
      {label.slice(0, at)}
      <strong>{label.slice(at, at + q.length)}</strong>
      {label.slice(at + q.length)}
    </>
  );
}

/**
 * One filter: a text field that suggests matching values as you type, five visible
 * at a time with the rest a scroll away.
 * Its options are narrowed by the other selections, so every choice still leads
 * somewhere; the current selection can be opened in the detail panel.
 */
function FilterSelect({
  label,
  placeholder,
  kind,
  value,
  onChange,
  onOpen,
  options,
}: {
  label: string;
  placeholder: string;
  kind: EntityRef["kind"];
  value: string;
  onChange: (value: string) => void;
  onOpen: (ref: EntityRef) => void;
  options: FilterOption[];
}) {
  const t = useT();
  const listId = useId();
  const listRef = useRef<HTMLUListElement>(null);
  const empty = options.length === 0 && !value;
  const selectedLabel = options.find((item) => String(item.id) === value)?.label ?? "";

  const [text, setText] = useState(selectedLabel);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  // Keep the field in step with the selection (e.g. after "Clear").
  useEffect(() => {
    setText(selectedLabel);
  }, [value, selectedLabel]);

  const matches = useMemo(
    () => suggest(options, text === selectedLabel && value ? "" : text),
    [options, text, selectedLabel, value],
  );

  // Keep the keyboard-highlighted suggestion in view as the arrows move past the fifth.
  useEffect(() => {
    if (!open) return;
    const row = listRef.current?.children[active] as HTMLElement | undefined;
    row?.scrollIntoView({ block: "nearest" });
  }, [active, open]);

  const choose = (item: FilterOption) => {
    setText(item.label);
    setOpen(false);
    onChange(String(item.id));
  };

  const type = (next: string) => {
    setText(next);
    setOpen(true);
    setActive(0);
    if (value) onChange("");
  };

  const keyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!open) setOpen(true);
      else setActive((i) => Math.min(i + 1, matches.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter" && open && matches[active]) {
      event.preventDefault();
      choose(matches[active]);
    } else if (event.key === "Escape" && open) {
      event.preventDefault();
      setOpen(false);
    }
  };

  const blur = () => {
    setOpen(false);
    // Free text that was never picked from the list is not a filter.
    if (!value) setText("");
  };

  const showList = open && !empty;

  return (
    <label className="combo">
      <span>{label}</span>
      <div className="combo-field">
        <input
          type="text"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showList && matches[active] ? `${listId}-${active}` : undefined}
          autoComplete="off"
          value={text}
          disabled={empty}
          placeholder={empty ? t("search.noneAvailable") : placeholder}
          onChange={(event) => type(event.target.value)}
          onFocus={() => {
            setOpen(true);
            setActive(0);
          }}
          onBlur={blur}
          onKeyDown={keyDown}
        />
        {showList && (
          <ul className="combo-list" id={listId} role="listbox" ref={listRef}>
            {matches.length === 0 ? (
              <li className="combo-empty">{t("search.noMatches")}</li>
            ) : (
              matches.map((item, index) => (
                <li
                  key={item.id}
                  id={`${listId}-${index}`}
                  role="option"
                  aria-selected={index === active}
                  className={index === active ? "active" : undefined}
                  // mousedown, not click: it fires before the input's blur closes the list.
                  onMouseDown={(event) => {
                    event.preventDefault();
                    choose(item);
                  }}
                  onMouseEnter={() => setActive(index)}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" className="combo-icon">
                    <circle cx="11" cy="11" r="6" fill="none" stroke="currentColor" strokeWidth="2" />
                    <path d="m20 20-4.2-4.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                  <span>
                    <Highlight label={item.label} query={text} />
                  </span>
                </li>
              ))
            )}
          </ul>
        )}
      </div>
      {value && (
        <button
          type="button"
          className="link-button filter-detail"
          onClick={() => onOpen({ kind, id: Number(value) })}
        >
          {t("search.viewDetails")}
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
