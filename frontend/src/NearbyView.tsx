import { NearbyMap } from "./NearbyMap";
import { formatDistance, sortByDistance } from "./viewerLocation";
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
  if (!location) {
    return (
      <section className="nearby">
        <h2>Institutions near you</h2>
        <p className="section-hint">
          Share a location and the catalogue is drawn on a map around it, nearest first.
          Nothing is shared until you choose to.
        </p>
        <button type="button" className="primary" onClick={onAsk}>
          Share a location
        </button>
      </section>
    );
  }

  const ranked = sortByDistance(institutions, location);

  return (
    <section className="nearby">
      <div className="results-heading">
        <h2>Institutions near you</h2>
        <span>{ranked.length} placed on the map</span>
      </div>

      <p className="section-hint">
        Measured from {location.label}.{" "}
        {location.source === "device"
          ? "This position stays in your browser."
          : "Only the address you typed was sent to the server."}
      </p>

      {ranked.length === 0 ? (
        <p className="empty">No institution in the catalogue has a location yet.</p>
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
                  <em className="role">{formatDistance(institution.distanceKm)}</em>
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
          Use a different location
        </button>
        <button type="button" className="link-button" onClick={onForget}>
          Forget my location
        </button>
      </div>
    </section>
  );
}
