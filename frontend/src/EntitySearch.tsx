import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { EntityKind, EntityMatch, EntityRef } from "./types";

/** What each kind is called where a result is shown. */
const KIND_LABEL: Record<EntityKind, string> = {
  institution: "Institution",
  researcher: "Researcher",
  instrument: "Instrument",
  analysis: "Analysis offering",
  microorganism: "Target organism",
  "instrument-type": "Instrument type",
  "analysis-type": "Analysis type",
};

const MIN_LENGTH = 2;
const DEBOUNCE_MS = 220;

/**
 * Find any record by a fragment of its name and open it.
 *
 * Typing is debounced, and every answer is checked against the query it was
 * asked for, so a slow reply for an earlier keystroke cannot overwrite a newer
 * one.
 */
export function EntitySearch({ onOpen }: { onOpen: (ref: EntityRef) => void }) {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<EntityMatch[] | null>(null);
  const [truncated, setTruncated] = useState(false);
  const [active, setActive] = useState(-1);
  const [error, setError] = useState("");
  const box = useRef<HTMLDivElement>(null);

  const term = query.trim();

  useEffect(() => {
    if (term.length < MIN_LENGTH) {
      setMatches(null);
      setError("");
      return;
    }
    let current = true;
    const timer = setTimeout(() => {
      api
        .findEntities(term)
        .then((answer) => {
          if (!current) return;
          setMatches(answer.items);
          setTruncated(answer.truncated);
          setActive(-1);
          setError("");
        })
        .catch((reason: unknown) => {
          if (!current) return;
          setMatches([]);
          setError(reason instanceof Error ? reason.message : "Search failed");
        });
    }, DEBOUNCE_MS);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [term]);

  // A click anywhere else puts the list away.
  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!box.current?.contains(event.target as Node)) setMatches(null);
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  const choose = (match: EntityMatch) => {
    onOpen({ kind: match.kind, id: match.id });
    setMatches(null);
    setQuery("");
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape") {
      setMatches(null);
      return;
    }
    if (!matches?.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((current) => (current + 1) % matches.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((current) => (current <= 0 ? matches.length - 1 : current - 1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(matches[active >= 0 ? active : 0]);
    }
  };

  const open = matches !== null;

  return (
    <div className="entity-search" ref={box}>
      <label>
        <span className="visually-hidden">Search everything by name</span>
        <input
          type="search"
          value={query}
          placeholder="Search institutions, instruments, analyses, organisms, researchers…"
          autoComplete="off"
          role="combobox"
          aria-expanded={open}
          aria-controls="entity-search-results"
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={onKeyDown}
        />
      </label>

      {open && (
        <div className="entity-results" id="entity-search-results" role="listbox">
          {error && <p className="error">{error}</p>}
          {!error && matches.length === 0 && (
            <p className="entity-empty">Nothing is named like “{term}”.</p>
          )}
          {matches.map((match, index) => (
            <button
              key={`${match.kind}-${match.id}`}
              type="button"
              className={index === active ? "entity-result active" : "entity-result"}
              role="option"
              aria-selected={index === active}
              onMouseEnter={() => setActive(index)}
              onClick={() => choose(match)}
            >
              <span className="entity-label">{highlight(match.label, term)}</span>
              <em className="entity-kind">{KIND_LABEL[match.kind]}</em>
              {match.note && <span className="entity-note">{match.note}</span>}
            </button>
          ))}
          {truncated && (
            <p className="entity-empty">More matches exist. Keep typing to narrow them.</p>
          )}
        </div>
      )}
    </div>
  );
}

/** Show why a result matched by marking the typed fragment inside the name. */
function highlight(label: string, term: string) {
  const at = label.toLowerCase().indexOf(term.toLowerCase());
  if (at < 0) return label;
  return (
    <>
      {label.slice(0, at)}
      <mark>{label.slice(at, at + term.length)}</mark>
      {label.slice(at + term.length)}
    </>
  );
}
