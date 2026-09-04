import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

/**
 * A small slippy map pinning one institution.
 *
 * Tiles come from OpenStreetMap, so the map needs internet access; without it
 * the marker and the controls still work over an empty background.
 *
 * The marker is a circle rather than Leaflet's default pin because the default
 * icon is loaded from image files whose bundled paths break under Vite.
 */
export function LocationMap({
  latitude,
  longitude,
  label,
}: {
  latitude: number;
  longitude: number;
  label: string;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!container.current || map.current) return;

    const instance = L.map(container.current, {
      center: [latitude, longitude],
      zoom: 13,
      scrollWheelZoom: true,
    });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(instance);
    L.circleMarker([latitude, longitude], {
      radius: 9,
      color: "#08775b",
      weight: 3,
      fillColor: "#08775b",
      fillOpacity: 0.35,
    })
      .addTo(instance)
      .bindPopup(label);

    map.current = instance;
    return () => {
      instance.remove();
      map.current = null;
    };
  }, []);

  // The panel animates in, so the map can be measured before it has its final
  // size. Re-checking once the position changes keeps the tiles aligned.
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    instance.invalidateSize();
    instance.setView([latitude, longitude], instance.getZoom());
  }, [latitude, longitude]);

  return (
    <div className="map-wrap">
      <div className="map" ref={container} role="application" aria-label={`Map of ${label}`} />
      <div className="map-hint">
        <span>
          {latitude.toFixed(4)}, {longitude.toFixed(4)}
        </span>
        <button
          type="button"
          className="link-button"
          onClick={() => map.current?.setView([latitude, longitude], 13)}
        >
          Recenter
        </button>
      </div>
    </div>
  );
}
