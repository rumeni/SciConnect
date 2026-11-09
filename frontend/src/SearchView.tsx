import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { useT, type MessageKey, type Translate } from "./i18n";
import type {
  EntityRef,
  CapabilityResult,
  FilterOptions,
  SearchResponse,
} from "./types";

export type Filters = {
  institution_ids: string;
  city: string;
  instrument_type_ids: string;
  analysis_type_ids: string;
  microorganism_ids: string;
  researcher_ids: string;
};

export const emptyFilters: Filters = {
  institution_ids: "",
  city: "",
  instrument_type_ids: "",
  analysis_type_ids: "",
  microorganism_ids: "",
  researcher_ids: "",
};

export function SearchView({
  options,
  filters,
  onFilterChange,
  onSearch,
  onLoadMore,
  onClear,
  applied,
  onRemoveFilter,
  filterLabel,
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
  applied: Filters;
  onRemoveFilter: (name: keyof Filters) => void;
  filterLabel: (name: keyof Filters, id: number) => string;
  onOpen: (ref: EntityRef) => void;
  results: SearchResponse | null;
  loading: boolean;
  error: string;
}) {
  const t = useT();
  // A city is its own value; there is no record behind it to open.
  const cityChoices = useMemo(
    () => (options.cities ?? []).map((city) => ({ id: city, label: city })),
    [options.cities],
  );

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
          label={t("search.city")}
          placeholder={t("search.placeholder.city")}
          value={filters.city}
          onChange={(value) => onFilterChange("city", value)}
          onOpen={onOpen}
          options={cityChoices}
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
        <AppliedFilters
          applied={applied}
          filterLabel={filterLabel}
          onRemove={onRemoveFilter}
        />
        <p className="results-hint">{t("search.hint")}</p>
        <div className="result-list">
          {results?.items.map((result) => (
            <ResultCard
              key={result.institution.id}
              result={result}
              applied={applied}
              onOpen={onOpen}
            />
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

/** A value a filter can take: a record id, or for the city its name. */
type Choice = { id: number | string; label: string };

/** Every option matching the query, ranked: whole-label prefixes first, then word prefixes, then anywhere. */
function suggest<T extends Choice>(options: T[], query: string): T[] {
  const q = fold(query.trim());
  if (!q) return options;
  const ranked: { item: T; rank: number }[] = [];
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
  /** The record kind behind the values, if any, so the choice can be opened. */
  kind?: EntityRef["kind"];
  value: string;
  onChange: (value: string) => void;
  onOpen: (ref: EntityRef) => void;
  options: Choice[];
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

  const choose = (item: Choice) => {
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
      {value && kind && (
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

/* --- Results ---------------------------------------------------------------- */

const FILTER_ORDER: (keyof Filters)[] = [
  "institution_ids",
  "city",
  "analysis_type_ids",
  "instrument_type_ids",
  "microorganism_ids",
  "researcher_ids",
];

const FILTER_TITLE: Record<keyof Filters, MessageKey> = {
  institution_ids: "search.institution",
  city: "search.city",
  instrument_type_ids: "search.instrument",
  analysis_type_ids: "search.analysis",
  microorganism_ids: "search.organism",
  researcher_ids: "search.researcher",
};

/** The filters the results were found with, each removable on its own. */
function AppliedFilters({
  applied,
  filterLabel,
  onRemove,
}: {
  applied: Filters;
  filterLabel: (name: keyof Filters, id: number) => string;
  onRemove: (name: keyof Filters) => void;
}) {
  const t = useT();
  const active = FILTER_ORDER.filter((name) => applied[name]);
  if (active.length === 0) return null;
  return (
    <div className="applied-filters">
      <span className="applied-title">{t("search.applied")}</span>
      {active.map((name) => {
        const label = name === "city" ? applied.city : filterLabel(name, Number(applied[name]));
        const remove = t("search.removeFilter", { name: label });
        return (
          <span className="applied-chip" key={name}>
            <span className="applied-kind">{t(FILTER_TITLE[name])}:</span> {label}
            <button type="button" aria-label={remove} title={remove} onClick={() => onRemove(name)}>
              ×
            </button>
          </span>
        );
      })}
    </div>
  );
}

/** Serbian counts take three forms (1 analiza, 2 analize, 5 analiza); English uses two. */
function counted(t: Translate, noun: "analysis" | "instrument" | "researcher", count: number) {
  const tens = count % 100;
  const ones = count % 10;
  const form =
    ones === 1 && tens !== 11
      ? "one"
      : ones >= 2 && ones <= 4 && (tens < 12 || tens > 14)
        ? "few"
        : "many";
  return t(`search.n.${noun}.${form}` as MessageKey, { count });
}

const AVAILABILITY = new Set(["available", "limited", "unavailable", "archived"]);

type Reason = { key: string; label: string; entity: EntityRef };

/** What in this result answers the search: the records behind each active filter. */
function matchReasons(result: CapabilityResult, applied: Filters): Reason[] {
  const reasons: Reason[] = [];
  const want = (name: keyof Filters) => (applied[name] ? Number(applied[name]) : null);

  const analysisType = want("analysis_type_ids");
  if (analysisType !== null) {
    for (const item of result.matched_analyses) {
      if (item.analysis_type_id !== analysisType) continue;
      reasons.push({
        key: `a${item.id}`,
        label: item.public_name || item.type_name,
        entity: { kind: "analysis", id: item.id },
      });
    }
  }
  const instrumentType = want("instrument_type_ids");
  if (instrumentType !== null) {
    for (const item of result.matched_instruments) {
      if (item.instrument_type_id !== instrumentType) continue;
      reasons.push({
        key: `i${item.id}`,
        label: item.display_name || item.type_name,
        entity: { kind: "instrument", id: item.id },
      });
    }
  }
  const organism = want("microorganism_ids");
  if (organism !== null) {
    const target = result.matched_analyses
      .flatMap((analysis) => analysis.targets)
      .find((item) => item.id === organism);
    if (target) {
      reasons.push({
        key: `m${target.id}`,
        label: target.scientific_name,
        entity: { kind: "microorganism", id: target.id },
      });
    }
  }
  const researcher = want("researcher_ids");
  if (researcher !== null) {
    const person =
      result.matched_researchers.find((item) => item.id === researcher) ??
      result.matched_analyses
        .flatMap((analysis) => analysis.researchers)
        .find((item) => item.id === researcher);
    if (person) {
      reasons.push({
        key: `r${person.id}`,
        label: person.full_name,
        entity: { kind: "researcher", id: person.id },
      });
    }
  }
  return reasons;
}

const SHOWN_ANALYSES = 3;
const SHOWN_CHIPS = 4;

/**
 * One institution, kept short: what it is, how much it offers, why it matched,
 * and its first few analyses. The rest opens in place or in the detail panel.
 */
function ResultCard({
  result,
  applied,
  onOpen,
}: {
  result: CapabilityResult;
  applied: Filters;
  onOpen: (ref: EntityRef) => void;
}) {
  const t = useT();
  const [expanded, setExpanded] = useState(false);
  const { institution, matched_analyses: analyses, matched_instruments: instruments } = result;

  // Everyone involved, listed once: staff and the people who run the analyses.
  const people = useMemo(() => {
    const seen = new Map<number, string>();
    for (const person of result.matched_researchers) seen.set(person.id, person.full_name);
    for (const analysis of result.matched_analyses) {
      for (const person of analysis.researchers) seen.set(person.id, person.full_name);
    }
    return [...seen].map(([id, name]) => ({ id, name }));
  }, [result]);

  const reasons = matchReasons(result, applied);
  const shownAnalyses = expanded ? analyses : analyses.slice(0, SHOWN_ANALYSES);
  const shownInstruments = expanded ? instruments : instruments.slice(0, SHOWN_CHIPS);
  const shownPeople = expanded ? people : people.slice(0, SHOWN_CHIPS);
  const hidden =
    analyses.length -
    shownAnalyses.length +
    instruments.length -
    shownInstruments.length +
    people.length -
    shownPeople.length;

  const summary = [
    analyses.length > 0 && counted(t, "analysis", analyses.length),
    instruments.length > 0 && counted(t, "instrument", instruments.length),
    people.length > 0 && counted(t, "researcher", people.length),
  ].filter(Boolean);

  const openInstitution = () => onOpen({ kind: "institution", id: institution.id });

  return (
    <article className="result-card">
      <header className="result-head">
        <div>
          <p className="location">
            {institution.city}, {institution.country}
          </p>
          <h3>
            <button type="button" className="title-button" onClick={openInstitution}>
              {institution.name}
            </button>
          </h3>
          {summary.length > 0 && <p className="result-summary">{summary.join(" · ")}</p>}
        </div>
        <button type="button" className="secondary result-open" onClick={openInstitution}>
          {t("search.openInstitution")} →
        </button>
      </header>

      {reasons.length > 0 && (
        <div className="result-why">
          <small>{t("search.matchesSearch")}</small>
          <div className="chips">
            {reasons.map((reason) => (
              <button
                key={reason.key}
                type="button"
                className="chip chip-match"
                onClick={() => onOpen(reason.entity)}
              >
                <span aria-hidden="true">✓</span> {reason.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {analyses.length > 0 && (
        <div className="result-block">
          <small>{t("search.analyses")}</small>
          <ul className="analysis-rows">
            {shownAnalyses.map((analysis) => (
              <li key={analysis.id}>
                <div className="analysis-line">
                  <button
                    type="button"
                    className="title-button strong"
                    onClick={() => onOpen({ kind: "analysis", id: analysis.id })}
                  >
                    {analysis.public_name || analysis.type_name}
                  </button>
                  {analysis.turnaround_days && (
                    <span className="analysis-meta">
                      {t("search.turnaround", { days: analysis.turnaround_days })}
                    </span>
                  )}
                  <span className={`availability availability-${analysis.availability}`}>
                    {AVAILABILITY.has(analysis.availability)
                      ? t(`status.${analysis.availability}` as MessageKey)
                      : analysis.availability}
                  </span>
                </div>
                {analysis.researchers.length > 0 && (
                  <p className="analysis-people">
                    {t("search.performedBy")}:{" "}
                    {analysis.researchers.map((person, index) => (
                      <span key={person.id}>
                        {index > 0 && ", "}
                        <button
                          type="button"
                          className="title-button"
                          onClick={() => onOpen({ kind: "researcher", id: person.id })}
                        >
                          {person.full_name}
                        </button>
                      </span>
                    ))}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {(instruments.length > 0 || people.length > 0) && (
        <div className="result-meta-grid">
          {instruments.length > 0 && (
            <div className="result-block">
              <small>{t("search.instruments")}</small>
              <div className="chips">
                {shownInstruments.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="chip"
                    onClick={() => onOpen({ kind: "instrument", id: item.id })}
                  >
                    {item.display_name || item.type_name}
                  </button>
                ))}
              </div>
            </div>
          )}
          {people.length > 0 && (
            <div className="result-block">
              <small>{t("search.researchers")}</small>
              <div className="chips">
                {shownPeople.map((person) => (
                  <button
                    key={person.id}
                    type="button"
                    className="chip"
                    onClick={() => onOpen({ kind: "researcher", id: person.id })}
                  >
                    {person.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {(expanded || hidden > 0) && (
        <button
          type="button"
          className="link-button result-toggle"
          aria-expanded={expanded}
          onClick={() => setExpanded((open) => !open)}
        >
          {expanded ? t("search.showLess") : `${t("search.showAll")} (+${hidden})`}
        </button>
      )}
    </article>
  );
}
