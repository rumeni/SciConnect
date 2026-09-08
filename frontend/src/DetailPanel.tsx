import { useEffect, useState } from "react";
import { api } from "./api";
import { LocationMap } from "./LocationMap";
import type {
  AnalysisRef,
  EntityDetail,
  EntityRef,
  InstitutionRef,
  InstrumentRef,
  PersonRef,
} from "./types";

/**
 * What the Remove button beside a row does.
 *
 * Some rows are connections, which can simply be severed. Others are records the
 * shown entity owns — an institution's researcher, for instance — and there the
 * only way to remove it from the owner is to delete it, because the affiliation
 * is a field of the record rather than a link. `detail` says which, so the
 * confirmation never hides that a record is about to go.
 */
type Removal = {
  detail: string;
  run: () => Promise<unknown>;
};

/** One clickable related record inside a detail view. */
type LinkItem = {
  ref: EntityRef;
  label: string;
  note?: string;
  badge?: string;
  remove?: Removal;
};

/** A detail response flattened into something the panel can render directly. */
type Content = {
  eyebrow: string;
  title: string;
  subtitle?: string;
  status?: string;
  map?: { latitude: number; longitude: number; label: string } | { missing: string };
  facts: { label: string; value: string }[];
  sections: { title: string; empty: string; items: LinkItem[] }[];
};

export function DetailPanel({
  stack,
  onOpen,
  onBack,
  onClose,
  onChanged,
}: {
  stack: EntityRef[];
  onOpen: (ref: EntityRef) => void;
  onBack: () => void;
  onClose: () => void;
  onChanged: () => void;
}) {
  const current = stack[stack.length - 1];
  const [detail, setDetail] = useState<EntityDetail | null>(null);
  const [error, setError] = useState("");
  // Bumped after a removal so the panel shows the record as it now stands.
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!current) return;
    let active = true;
    setDetail(null);
    setError("");
    api
      .detail(current)
      .then((result) => {
        if (active) setDetail(result);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load");
      });
    return () => {
      active = false;
    };
  }, [current?.kind, current?.id, version]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!current) return null;

  const content = detail ? describe(detail) : null;

  return (
    <div className="detail-backdrop" onClick={onClose} role="presentation">
      <aside
        className="detail-panel"
        role="dialog"
        aria-modal="true"
        aria-label={content?.title ?? "Details"}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="detail-bar">
          {stack.length > 1 ? (
            <button type="button" className="link-button" onClick={onBack}>
              ← Back
            </button>
          ) : (
            <span />
          )}
          <button type="button" className="link-button" onClick={onClose}>
            Close ✕
          </button>
        </div>

        {error && <p className="error">{error}</p>}
        {!detail && !error && <p className="empty">Loading…</p>}

        {content && (
          <>
            <header className="detail-head">
              <p className="eyebrow">{content.eyebrow}</p>
              <h2>{content.title}</h2>
              {content.subtitle && <p className="detail-subtitle">{content.subtitle}</p>}
              {content.status && <span className="badge">{content.status}</span>}
            </header>

            {content.map && (
              <section className="detail-section">
                <h3>Location</h3>
                {"missing" in content.map ? (
                  <p className="empty">{content.map.missing}</p>
                ) : (
                  <LocationMap
                    key={`${content.map.latitude},${content.map.longitude}`}
                    latitude={content.map.latitude}
                    longitude={content.map.longitude}
                    label={content.map.label}
                  />
                )}
              </section>
            )}

            {content.facts.length > 0 && (
              <dl className="facts">
                {content.facts.map((fact) => (
                  <div key={fact.label}>
                    <dt>{fact.label}</dt>
                    <dd>{fact.value}</dd>
                  </div>
                ))}
              </dl>
            )}

            {content.sections.map((section) => (
              <section className="detail-section" key={section.title}>
                <h3>{section.title}</h3>
                {section.items.length === 0 ? (
                  <p className="empty">{section.empty}</p>
                ) : (
                  <ul className="link-list">
                    {section.items.map((item) => (
                      <li key={`${item.ref.kind}-${item.ref.id}`} className="link-entry">
                        <button
                          type="button"
                          className="link-row"
                          onClick={() => onOpen(item.ref)}
                        >
                          <span className="link-label">{item.label}</span>
                          {item.badge && <em className="role">{item.badge}</em>}
                          {item.note && <span className="link-note">{item.note}</span>}
                        </button>
                        {item.remove && (
                          <RowRemoval
                            removal={item.remove}
                            onDone={() => {
                              setVersion((count) => count + 1);
                              onChanged();
                            }}
                          />
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            ))}
          </>
        )}
      </aside>
    </div>
  );
}

/** The Remove button beside a row, with its own confirmation. */
function RowRemoval({ removal, onDone }: { removal: Removal; onDone: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    setBusy(true);
    setError("");
    try {
      await removal.run();
      onDone();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not remove");
      setBusy(false);
      setConfirming(false);
    }
  };

  if (!confirming) {
    return (
      <div className="row-removal">
        <button type="button" className="danger" onClick={() => setConfirming(true)}>
          Remove
        </button>
        {error && <p className="form-error">{error}</p>}
      </div>
    );
  }

  return (
    <div className="row-removal confirming">
      <p className="removal-detail">{removal.detail}</p>
      <div className="removal-actions">
        <button type="button" className="danger" disabled={busy} onClick={() => void run()}>
          {busy ? "Removing…" : "Yes, remove"}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() => setConfirming(false)}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

const instrumentLabel = (item: InstrumentRef) => item.display_name || item.type_name;
const analysisLabel = (item: AnalysisRef) => item.public_name || item.type_name;

const instrumentItem = (item: InstrumentRef, remove?: Removal): LinkItem => ({
  ref: { kind: "instrument", id: item.id },
  label: instrumentLabel(item),
  badge: item.usage ?? undefined,
  note: [item.manufacturer, item.model].filter(Boolean).join(" ") || item.status,
  remove,
});

const analysisItem = (item: AnalysisRef, remove?: Removal): LinkItem => ({
  ref: { kind: "analysis", id: item.id },
  label: analysisLabel(item),
  badge: item.role ?? item.usage ?? undefined,
  note: item.institution ? item.institution.name : item.availability,
  remove,
});

const personItem = (item: PersonRef, remove?: Removal): LinkItem => ({
  ref: { kind: "researcher", id: item.id },
  label: item.full_name,
  badge: item.role ?? undefined,
  note: item.title ?? item.institution?.name ?? undefined,
  remove,
});

/** Removing an owned record from its owner means deleting it. */
const deletes = (ref: EntityRef, owner: string, what: string): Removal => ({
  detail:
    `Removes this ${what} from ${owner}. The record is deleted, ` +
    "because it belongs to exactly one institution and cannot stand without it.",
  run: () => api.removeEntity(ref),
});

const unlinksInstrument = (analysisId: number, instrumentId: number): Removal => ({
  detail: "The offering stops using this instrument. Both records stay.",
  run: () => api.unlinkInstrument(analysisId, instrumentId),
});

const unlinksTarget = (analysisId: number, microorganismId: number): Removal => ({
  detail: "The offering stops detecting this organism. Both records stay.",
  run: () => api.unlinkTarget(analysisId, microorganismId),
});

const unlinksResearcher = (analysisId: number, researcherId: number): Removal => ({
  detail: "They stop performing this offering. Both records stay.",
  run: () => api.unlinkResearcher(analysisId, researcherId),
});

const institutionItem = (item: InstitutionRef): LinkItem => ({
  ref: { kind: "institution", id: item.id },
  label: item.name,
  note: `${item.city}, ${item.country}`,
});

const fact = (label: string, value: string | number | null | undefined) =>
  value === null || value === undefined || value === "" ? [] : [{ label, value: String(value) }];

function describe(detail: EntityDetail): Content {
  switch (detail.kind) {
    case "institution": {
      const item = detail.data;
      return {
        eyebrow: "Institution",
        title: item.name,
        subtitle: item.description ?? undefined,
        status: item.status,
        map:
          item.latitude !== null && item.longitude !== null
            ? { latitude: item.latitude, longitude: item.longitude, label: item.name }
            : {
                missing: item.address
                  ? "This address could not be placed on a map."
                  : "No address recorded for this institution.",
              },
        facts: [
          ...fact("Address", item.address),
          ...fact("Location", `${item.city}, ${item.country}`),
          ...fact("Website", item.website),
          ...fact("Contact", item.contact_email),
          ...fact("Slug", item.slug),
        ],
        sections: [
          {
            title: "Instruments",
            empty: "No instruments recorded.",
            items: item.instruments.map((unit) =>
              instrumentItem(
                unit,
                deletes({ kind: "instrument", id: unit.id }, item.name, "instrument"),
              ),
            ),
          },
          {
            title: "Analysis offerings",
            empty: "No analysis offerings recorded.",
            items: item.analyses.map((offering) =>
              analysisItem(
                offering,
                deletes({ kind: "analysis", id: offering.id }, item.name, "offering"),
              ),
            ),
          },
          {
            title: "Researchers",
            empty: "No researchers recorded.",
            items: item.researchers.map((person) =>
              personItem(
                person,
                deletes({ kind: "researcher", id: person.id }, item.name, "researcher"),
              ),
            ),
          },
        ],
      };
    }
    case "researcher": {
      const item = detail.data;
      return {
        eyebrow: "Researcher",
        title: item.full_name,
        subtitle: item.expertise ?? undefined,
        status: item.status,
        facts: [
          ...fact("Title", item.title),
          ...fact("Email", item.email),
          ...fact("ORCID", item.orcid),
        ],
        sections: [
          {
            title: "Institution",
            empty: "",
            items: [institutionItem(item.institution)],
          },
          {
            title: "Performs",
            empty: "Not linked to any analysis offering yet.",
            items: item.analyses.map((offering) =>
              analysisItem(offering, unlinksResearcher(offering.id, item.id)),
            ),
          },
        ],
      };
    }
    case "instrument": {
      const item = detail.data;
      return {
        eyebrow: "Instrument",
        title: item.display_name || item.instrument_type.name,
        subtitle: item.access_notes ?? undefined,
        status: item.status,
        facts: [
          ...fact("Type", item.instrument_type.name),
          ...fact("Manufacturer", item.manufacturer),
          ...fact("Model", item.model),
        ],
        sections: [
          { title: "Institution", empty: "", items: [institutionItem(item.institution)] },
          {
            title: "Instrument type",
            empty: "",
            items: [
              {
                ref: { kind: "instrument-type", id: item.instrument_type.id },
                label: item.instrument_type.name,
                note: item.instrument_type.description ?? undefined,
              },
            ],
          },
          {
            title: "Used by",
            empty: "Not linked to any analysis offering yet.",
            items: item.analyses.map((offering) =>
              analysisItem(offering, unlinksInstrument(offering.id, item.id)),
            ),
          },
        ],
      };
    }
    case "analysis": {
      const item = detail.data;
      return {
        eyebrow: "Analysis offering",
        title: item.public_name || item.analysis_type.name,
        subtitle: item.description ?? undefined,
        status: item.availability,
        facts: [
          ...fact("Analysis type", item.analysis_type.name),
          ...fact(
            "Turnaround",
            item.turnaround_days ? `${item.turnaround_days} days` : null,
          ),
        ],
        sections: [
          { title: "Institution", empty: "", items: [institutionItem(item.institution)] },
          {
            title: "Analysis type",
            empty: "",
            items: [
              {
                ref: { kind: "analysis-type", id: item.analysis_type.id },
                label: item.analysis_type.name,
                note: item.analysis_type.description ?? undefined,
              },
            ],
          },
          {
            title: "Uses instruments",
            empty: "No instrument linked yet.",
            items: item.instruments.map((unit) =>
              instrumentItem(unit, unlinksInstrument(item.id, unit.id)),
            ),
          },
          {
            title: "Target organisms",
            empty: "No target organism linked yet.",
            items: item.targets.map((target) => ({
              ref: { kind: "microorganism" as const, id: target.id },
              label: target.scientific_name,
              note: target.common_name ?? undefined,
              remove: unlinksTarget(item.id, target.id),
            })),
          },
          {
            title: "Performed by",
            empty: "No researcher linked yet.",
            items: item.researchers.map((person) =>
              personItem(person, unlinksResearcher(item.id, person.id)),
            ),
          },
        ],
      };
    }
    case "microorganism": {
      const item = detail.data;
      return {
        eyebrow: "Target organism",
        title: item.scientific_name,
        subtitle: item.description ?? undefined,
        facts: fact("Common name", item.common_name),
        sections: [
          {
            title: "Detected by",
            empty: "No analysis offering targets this organism yet.",
            items: item.analyses.map((offering) =>
              analysisItem(offering, unlinksTarget(offering.id, item.id)),
            ),
          },
        ],
      };
    }
    case "instrument-type": {
      const item = detail.data;
      return {
        eyebrow: "Instrument type",
        title: item.name,
        subtitle: item.description ?? undefined,
        facts: [],
        sections: [
          {
            title: "Institutions owning one",
            empty: "No institution owns this instrument type yet.",
            items: item.institutions.map(institutionItem),
          },
          {
            title: "Individual units",
            empty: "No units recorded.",
            items: item.instruments.map((unit) =>
              instrumentItem(
                unit,
                deletes({ kind: "instrument", id: unit.id }, "its institution", "instrument"),
              ),
            ),
          },
        ],
      };
    }
    case "analysis-type": {
      const item = detail.data;
      return {
        eyebrow: "Analysis type",
        title: item.name,
        subtitle: item.description ?? undefined,
        facts: [],
        sections: [
          {
            title: "Institutions offering it",
            empty: "No institution offers this analysis type yet.",
            items: item.institutions.map(institutionItem),
          },
          {
            title: "Offerings",
            empty: "No offerings recorded.",
            items: item.analyses.map((offering) =>
              analysisItem(
                offering,
                deletes({ kind: "analysis", id: offering.id }, "its institution", "offering"),
              ),
            ),
          },
        ],
      };
    }
  }
}
