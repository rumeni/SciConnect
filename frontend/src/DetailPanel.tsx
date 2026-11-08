import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { useT, type Translate } from "./i18n";
import { LocationMap } from "./LocationMap";
import { useDialog } from "./useDialog";
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
  canEdit,
}: {
  stack: EntityRef[];
  onOpen: (ref: EntityRef) => void;
  onBack: () => void;
  onClose: () => void;
  onChanged: () => void;
  /**
   * Whether to offer Remove beside each row. A guest is shown none: the server
   * would refuse the request anyway, and a button that can only fail is noise.
   */
  canEdit: boolean;
}) {
  const t = useT();
  const current = stack[stack.length - 1];
  const [detail, setDetail] = useState<EntityDetail | null>(null);
  const [error, setError] = useState("");
  // Bumped after a removal so the panel shows the record as it now stands.
  const [version, setVersion] = useState(0);
  const panel = useRef<HTMLElement>(null);
  useDialog(Boolean(current), panel);

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
        if (active) setError(reason instanceof Error ? reason.message : t("detail.couldNotLoad"));
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

  const content = detail ? describe(detail, t) : null;

  return (
    <div className="detail-backdrop" onClick={onClose} role="presentation">
      <aside
        ref={panel}
        className="detail-panel"
        role="dialog"
        aria-modal="true"
        aria-label={content?.title ?? t("detail.title")}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="detail-bar">
          {stack.length > 1 ? (
            <button type="button" className="link-button" onClick={onBack}>
              ← {t("common.back")}
            </button>
          ) : (
            <span />
          )}
          <button type="button" className="link-button" onClick={onClose}>
            {t("common.close")} ✕
          </button>
        </div>

        {error && <p className="error">{error}</p>}
        {!detail && !error && <p className="empty">{t("common.loading")}</p>}

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
                <h3>{t("detail.location")}</h3>
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
                        {canEdit && item.remove && (
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
  const t = useT();
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
      setError(reason instanceof Error ? reason.message : t("detail.couldNotRemove"));
      setBusy(false);
      setConfirming(false);
    }
  };

  if (!confirming) {
    return (
      <div className="row-removal">
        <button type="button" className="danger" onClick={() => setConfirming(true)}>
          {t("common.remove")}
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
          {busy ? t("common.removing") : t("detail.yesRemove")}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() => setConfirming(false)}
        >
          {t("common.cancel")}
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

/** Which kind of owned record a deletion is about, for the warning's wording. */
type Owned = "instrument" | "offering" | "researcher";

/** Removing an owned record from its owner means deleting it. */
const deletes = (t: Translate, ref: EntityRef, owner: string, what: Owned): Removal => ({
  detail: t("detail.remove.deletes", {
    what: t(`detail.remove.what.${what}` as const),
    owner,
  }),
  run: () => api.removeEntity(ref),
});

const unlinksInstrument = (
  t: Translate,
  analysisId: number,
  instrumentId: number,
): Removal => ({
  detail: t("detail.remove.instrument"),
  run: () => api.unlinkInstrument(analysisId, instrumentId),
});

const unlinksTarget = (
  t: Translate,
  analysisId: number,
  microorganismId: number,
): Removal => ({
  detail: t("detail.remove.target"),
  run: () => api.unlinkTarget(analysisId, microorganismId),
});

const unlinksResearcher = (
  t: Translate,
  analysisId: number,
  researcherId: number,
): Removal => ({
  detail: t("detail.remove.researcher"),
  run: () => api.unlinkResearcher(analysisId, researcherId),
});

const institutionItem = (item: InstitutionRef): LinkItem => ({
  ref: { kind: "institution", id: item.id },
  label: item.name,
  note: `${item.city}, ${item.country}`,
});

/** An offering listed under its type, removable only by deleting it. */
const ownedAnalysisItem = (t: Translate, offering: AnalysisRef): LinkItem =>
  analysisItem(
    offering,
    deletes(
      t,
      { kind: "analysis", id: offering.id },
      t("detail.remove.itsInstitution"),
      "offering",
    ),
  );

const fact = (label: string, value: string | number | null | undefined) =>
  value === null || value === undefined || value === "" ? [] : [{ label, value: String(value) }];

function describe(detail: EntityDetail, t: Translate): Content {
  switch (detail.kind) {
    case "institution": {
      const item = detail.data;
      return {
        eyebrow: t("kind.institution"),
        title: item.name,
        subtitle: item.description ?? undefined,
        status: item.status,
        map:
          item.latitude !== null && item.longitude !== null
            ? { latitude: item.latitude, longitude: item.longitude, label: item.name }
            : {
                missing: item.address ? t("detail.noMapAddress") : t("detail.noAddress"),
              },
        facts: [
          ...fact(t("detail.fact.address"), item.address),
          ...fact(t("detail.fact.location"), `${item.city}, ${item.country}`),
          ...fact(t("detail.fact.website"), item.website),
          ...fact(t("detail.fact.contact"), item.contact_email),
          ...fact(t("detail.fact.slug"), item.slug),
        ],
        sections: [
          {
            title: t("detail.section.instruments"),
            empty: t("detail.section.instruments.empty"),
            items: item.instruments.map((unit) =>
              instrumentItem(
                unit,
                deletes(t, { kind: "instrument", id: unit.id }, item.name, "instrument"),
              ),
            ),
          },
          {
            title: t("detail.section.analyses"),
            empty: t("detail.section.analyses.empty"),
            items: item.analyses.map((offering) =>
              analysisItem(
                offering,
                deletes(t, { kind: "analysis", id: offering.id }, item.name, "offering"),
              ),
            ),
          },
          {
            title: t("detail.section.researchers"),
            empty: t("detail.section.researchers.empty"),
            items: item.researchers.map((person) =>
              personItem(
                person,
                deletes(t, { kind: "researcher", id: person.id }, item.name, "researcher"),
              ),
            ),
          },
        ],
      };
    }
    case "researcher": {
      const item = detail.data;
      return {
        eyebrow: t("kind.researcher"),
        title: item.full_name,
        subtitle: item.expertise ?? undefined,
        status: item.status,
        facts: [
          ...fact(t("detail.fact.title"), item.title),
          ...fact(t("detail.fact.email"), item.email),
          ...fact(t("detail.fact.orcid"), item.orcid),
        ],
        sections: [
          {
            title: t("detail.section.institution"),
            empty: "",
            items: [institutionItem(item.institution)],
          },
          {
            title: t("detail.section.performs"),
            empty: t("detail.section.performs.empty"),
            items: item.analyses.map((offering) =>
              analysisItem(offering, unlinksResearcher(t, offering.id, item.id)),
            ),
          },
        ],
      };
    }
    case "instrument": {
      const item = detail.data;
      return {
        eyebrow: t("kind.instrument"),
        title: item.display_name || item.instrument_type.name,
        subtitle: item.access_notes ?? undefined,
        status: item.status,
        facts: [
          ...fact(t("detail.fact.type"), item.instrument_type.name),
          ...fact(t("detail.fact.manufacturer"), item.manufacturer),
          ...fact(t("detail.fact.model"), item.model),
        ],
        sections: [
          {
            title: t("detail.section.institution"),
            empty: "",
            items: [institutionItem(item.institution)],
          },
          {
            title: t("detail.section.instrumentType"),
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
            title: t("detail.section.usedBy"),
            empty: t("detail.section.usedBy.empty"),
            items: item.analyses.map((offering) =>
              analysisItem(offering, unlinksInstrument(t, offering.id, item.id)),
            ),
          },
        ],
      };
    }
    case "analysis": {
      const item = detail.data;
      return {
        eyebrow: t("kind.analysis"),
        title: item.public_name || item.analysis_type.name,
        subtitle: item.description ?? undefined,
        status: item.availability,
        facts: [
          ...fact(t("detail.fact.analysisType"), item.analysis_type.name),
          ...fact(
            t("detail.fact.turnaround"),
            item.turnaround_days
              ? t("detail.fact.turnaroundDays", { days: item.turnaround_days })
              : null,
          ),
        ],
        sections: [
          {
            title: t("detail.section.institution"),
            empty: "",
            items: [institutionItem(item.institution)],
          },
          {
            title: t("detail.section.analysisType"),
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
            title: t("detail.section.usesInstruments"),
            empty: t("detail.section.usesInstruments.empty"),
            items: item.instruments.map((unit) =>
              instrumentItem(unit, unlinksInstrument(t, item.id, unit.id)),
            ),
          },
          {
            title: t("detail.section.targets"),
            empty: t("detail.section.targets.empty"),
            items: item.targets.map((target) => ({
              ref: { kind: "microorganism" as const, id: target.id },
              label: target.scientific_name,
              note: target.common_name ?? undefined,
              remove: unlinksTarget(t, item.id, target.id),
            })),
          },
          {
            title: t("detail.section.performedBy"),
            empty: t("detail.section.performedBy.empty"),
            items: item.researchers.map((person) =>
              personItem(person, unlinksResearcher(t, item.id, person.id)),
            ),
          },
        ],
      };
    }
    case "microorganism": {
      const item = detail.data;
      return {
        eyebrow: t("kind.microorganism"),
        title: item.scientific_name,
        subtitle: item.description ?? undefined,
        facts: fact(t("detail.fact.commonName"), item.common_name),
        sections: [
          {
            title: t("detail.section.detectedBy"),
            empty: t("detail.section.detectedBy.empty"),
            items: item.analyses.map((offering) =>
              analysisItem(offering, unlinksTarget(t, offering.id, item.id)),
            ),
          },
        ],
      };
    }
    case "instrument-type": {
      const item = detail.data;
      return {
        eyebrow: t("kind.instrument-type"),
        title: item.name,
        subtitle: item.description ?? undefined,
        facts: [],
        sections: [
          {
            title: t("detail.section.owners"),
            empty: t("detail.section.owners.empty"),
            items: item.institutions.map(institutionItem),
          },
          {
            title: t("detail.section.units"),
            empty: t("detail.section.units.empty"),
            items: item.instruments.map((unit) =>
              instrumentItem(
                unit,
                deletes(
                  t,
                  { kind: "instrument", id: unit.id },
                  t("detail.remove.itsInstitution"),
                  "instrument",
                ),
              ),
            ),
          },
        ],
      };
    }
    case "analysis-type": {
      const item = detail.data;
      return {
        eyebrow: t("kind.analysis-type"),
        title: item.name,
        subtitle: item.description ?? undefined,
        facts: [],
        sections: [
          {
            title: t("detail.section.offerers"),
            empty: t("detail.section.offerers.empty"),
            items: item.institutions.map(institutionItem),
          },
          {
            title: t("detail.section.offerings"),
            empty: t("detail.section.offerings.empty"),
            items: item.analyses.map((offering) => ownedAnalysisItem(t, offering)),
          },
        ],
      };
    }
  }
}
