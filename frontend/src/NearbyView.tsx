import { useState } from "react";
import { useT } from "./i18n";
import { NearbyMap } from "./NearbyMap";
import { formatDistance, placeName, sortByDistance } from "./viewerLocation";
import type { EntityRef, InstitutionMapPoint, ViewerLocation } from "./types";

export function NearbyView({
  location,
  institutions,
  matching,
  onOpen,
  onAsk,
  onForget,
}: {
  location: ViewerLocation | null;
  institutions: InstitutionMapPoint[];
  /** Institutions found by the last filtered search, or null when nothing was filtered. */
  matching: Set<number> | null;
  onOpen: (ref: EntityRef) => void;
  onAsk: () => void;
  onForget: () => void;
}) {
  const t = useT();
  const [onlyMatches, setOnlyMatches] = useState(false);

  if (!location) {
    return (
      <section className="nearby">
        <h2>{t("nearby.title")}</h2>
        <p className="section-hint">{t("nearby.intro")}</p>
        <button type="button" className="primary" onClick={onAsk}>
          {t("nearby.share")}
        </button>
      </section>
    );
  }

  const everyone = sortByDistance(institutions, location);
  const matchCount = matching ? everyone.filter((item) => matching.has(item.id)).length : 0;
  const ranked =
    matching && onlyMatches ? everyone.filter((item) => matching.has(item.id)) : everyone;

  return (
    <section className="nearby">
      <div className="results-heading">
        <h2>{t("nearby.title")}</h2>
        <span>{t("nearby.placed", { count: ranked.length })}</span>
      </div>

      <p className="section-hint">
        {t("nearby.measuredFrom", { place: placeName(location, t) })}{" "}
        {location.source === "device" ? t("nearby.deviceNote") : t("nearby.addressNote")}
      </p>

      {matching && (
        <div className="nearby-legend">
          <span className="legend-item">
            <span className="legend-dot legend-match" aria-hidden="true" />
            {t("nearby.legendMatch", { count: matchCount })}
          </span>
          {!onlyMatches && (
            <span className="legend-item">
              <span className="legend-dot legend-other" aria-hidden="true" />
              {t("nearby.legendOther")}
            </span>
          )}
          <label className="legend-toggle">
            <input
              type="checkbox"
              checked={onlyMatches}
              onChange={(event) => setOnlyMatches(event.target.checked)}
            />
            {t("nearby.onlyMatches")}
          </label>
        </div>
      )}

      {ranked.length === 0 ? (
        <p className="empty">{t("nearby.none")}</p>
      ) : (
        <>
          <NearbyMap
            origin={location}
            institutions={ranked}
            matching={matching}
            onOpen={onOpen}
          />
          <ul className="link-list nearby-list">
            {ranked.map((institution) => (
              <li key={institution.id}>
                <button
                  type="button"
                  className={
                    matching && !matching.has(institution.id) ? "link-row link-row-faded" : "link-row"
                  }
                  onClick={() => onOpen({ kind: "institution", id: institution.id })}
                >
                  <span className="link-label">{institution.name}</span>
                  <em className="role">{formatDistance(institution.distanceKm, t)}</em>
                  {matching?.has(institution.id) && (
                    <em className="match-tag">{t("nearby.matchTag")}</em>
                  )}
                  <span className="link-note">
                    {institution.address
                      ? `${institution.address}, ${institution.city}`
                      : `${institution.city}, ${institution.country}`}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      <div className="nearby-actions">
        <button type="button" className="secondary" onClick={onAsk}>
          {t("nearby.different")}
        </button>
        <button type="button" className="link-button" onClick={onForget}>
          {t("nearby.forget")}
        </button>
      </div>
    </section>
  );
}
