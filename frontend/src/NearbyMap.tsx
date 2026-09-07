import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { addBaseLayer, institutionMarker, viewerMarker } from "./mapLayer";
import { formatDistance, type NearbyInstitution } from "./viewerLocation";
import type { EntityRef, ViewerLocation } from "./types";

/** A zoomable map of the catalogue around one point, nearest institutions marked. */
export function NearbyMap({
  origin,
  institutions,
  onOpen,
}: {
  origin: ViewerLocation;
  institutions: NearbyInstitution[];
  onOpen: (ref: EntityRef) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  // Read inside Leaflet popup handlers, which outlive the render that made them.
  const open = useRef(onOpen);
  open.current = onOpen;

  useEffect(() => {
    if (!container.current || map.current) return;
    const instance = L.map(container.current, { scrollWheelZoom: true });
    addBaseLayer(instance);
    map.current = instance;
    return () => {
      instance.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;

    const drawn: L.Layer[] = [];
    const here = viewerMarker(origin.latitude, origin.longitude)
      .bindPopup(origin.label)
      .addTo(instance);
    drawn.push(here);

    for (const institution of institutions) {
      const marker = institutionMarker(institution.latitude, institution.longitude).addTo(
        instance,
      );
      const popup = document.createElement("div");
      popup.className = "map-popup";
      const name = document.createElement("button");
      name.type = "button";
      name.className = "title-button strong";
      name.textContent = institution.name;
      name.onclick = () => open.current({ kind: "institution", id: institution.id });
      const note = document.createElement("small");
      note.textContent = `${institution.city} · ${formatDistance(institution.distanceKm)}`;
      popup.append(name, note);
      marker.bindPopup(popup);
      drawn.push(marker);
    }

    const bounds = L.latLngBounds([
      [origin.latitude, origin.longitude],
      ...institutions.map(
        (item) => [item.latitude, item.longitude] as [number, number],
      ),
    ]);
    instance.invalidateSize();
    instance.fitBounds(bounds, { padding: [36, 36], maxZoom: 13 });

    return () => {
      drawn.forEach((layer) => layer.remove());
    };
  }, [origin.latitude, origin.longitude, origin.label, institutions]);

  return (
    <div className="map-wrap">
      <div
        className="map map-tall"
        ref={container}
        role="application"
        aria-label="Map of institutions near you"
      />
      <div className="map-hint">
        <span>{origin.label}</span>
        <button
          type="button"
          className="link-button"
          onClick={() =>
            map.current?.setView([origin.latitude, origin.longitude], 12)
          }
        >
          Recenter
        </button>
      </div>
    </div>
  );
}
