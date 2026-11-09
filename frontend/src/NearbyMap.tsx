import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useT } from "./i18n";
import {
  addBaseLayer,
  institutionMarker,
  popupNode,
  viewerMarker,
  type MarkerTone,
} from "./mapLayer";
import { formatDistance, placeName, type NearbyInstitution } from "./viewerLocation";
import type { EntityRef, ViewerLocation } from "./types";

/**
 * A zoomable map of the catalogue around one point, nearest institutions marked.
 * With `matching` set, institutions that answer the current search are drawn
 * green and the rest faded grey, and the view frames the matches.
 */
export function NearbyMap({
  origin,
  institutions,
  matching,
  onOpen,
}: {
  origin: ViewerLocation;
  institutions: NearbyInstitution[];
  matching: Set<number> | null;
  onOpen: (ref: EntityRef) => void;
}) {
  const t = useT();
  const originLabel = placeName(origin, t);
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  // Read inside Leaflet popup handlers, which outlive the render that made them.
  const open = useRef(onOpen);
  open.current = onOpen;
  // Popups are built imperatively, so the translator is read the same way.
  const say = useRef(t);
  say.current = t;

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
      .bindPopup(popupNode(originLabel))
      .addTo(instance);
    drawn.push(here);

    const toneOf = (id: number): MarkerTone =>
      matching ? (matching.has(id) ? "match" : "other") : "plain";
    // Non-matches first, so the matches are drawn on top of them.
    const ordered = [...institutions].sort(
      (a, b) => Number(toneOf(a.id) === "match") - Number(toneOf(b.id) === "match"),
    );

    for (const institution of ordered) {
      const marker = institutionMarker(
        institution.latitude,
        institution.longitude,
        toneOf(institution.id),
      ).addTo(instance);
      const popup = document.createElement("div");
      popup.className = "map-popup";
      const name = document.createElement("button");
      name.type = "button";
      name.className = "title-button strong";
      name.textContent = institution.name;
      name.onclick = () => open.current({ kind: "institution", id: institution.id });
      const note = document.createElement("small");
      note.textContent = `${institution.city} · ${formatDistance(
        institution.distanceKm,
        say.current,
      )}`;
      popup.append(name, note);
      marker.bindPopup(popup);
      drawn.push(marker);
    }

    // Frame the matches when there are any; otherwise everything shown.
    const matched = matching ? institutions.filter((item) => matching.has(item.id)) : [];
    const framed = matched.length > 0 ? matched : institutions;
    const bounds = L.latLngBounds([
      [origin.latitude, origin.longitude],
      ...framed.map((item) => [item.latitude, item.longitude] as [number, number]),
    ]);
    instance.invalidateSize();
    instance.fitBounds(bounds, { padding: [36, 36], maxZoom: 13 });

    return () => {
      drawn.forEach((layer) => layer.remove());
    };
  }, [origin.latitude, origin.longitude, originLabel, institutions, matching]);

  return (
    <div className="map-wrap">
      <div
        className="map map-tall"
        ref={container}
        role="application"
        aria-label={t("nearby.mapLabel")}
      />
      <div className="map-hint">
        <span>{originLabel}</span>
        <button
          type="button"
          className="link-button"
          onClick={() =>
            map.current?.setView([origin.latitude, origin.longitude], 12)
          }
        >
          {t("common.recenter")}
        </button>
      </div>
    </div>
  );
}
