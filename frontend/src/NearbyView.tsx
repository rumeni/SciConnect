import { useT } from "./i18n";
import { NearbyMap } from "./NearbyMap";
import { formatDistance, placeName, sortByDistance } from "./viewerLocation";
import type { EntityRef, InstitutionMapPoint, ViewerLocation } from "./types";

export function NearbyView({
  location,
  institutions,
  onOpen,
  onAsk,
  onForget,
}: {
  location: ViewerLocation | null;
  institutions: InstitutionMapPoint[];
  onOpen: (ref: EntityRef) => void;
  onAsk: () => void;
  onForget: () => void;
}) {
  const t = useT();

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

  const ranked = sortByDistance(institutions, location);

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

      {ranked.length === 0 ? (
        <p className="empty">{t("nearby.none")}</p>
      ) : (
        <>
          <NearbyMap origin={location} institutions={ranked} onOpen={onOpen} />
          <ul className="link-list nearby-list">
            {ranked.map((institution) => (
              <li key={institution.id}>
                <button
                  type="button"
                  className="link-row"
                  onClick={() => onOpen({ kind: "institution", id: institution.id })}
                >
                  <span className="link-label">{institution.name}</span>
                  <em className="role">{formatDistance(institution.distanceKm, t)}</em>
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
