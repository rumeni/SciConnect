import L from "leaflet";

const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

/** Tiles are the only part of a map that needs the network. */
export function addBaseLayer(map: L.Map): void {
  L.tileLayer(TILE_URL, { maxZoom: 19, attribution: ATTRIBUTION }).addTo(map);
}

/**
 * How an institution is drawn: `plain` when nothing is being searched for,
 * `match` when it answers the current search, `other` when it does not.
 * Non-matches are faded grey rather than red, so they read as "not this time"
 * and not as an error, and the matches stand out.
 */
export type MarkerTone = "plain" | "match" | "other";

const MARKER_STYLE: Record<MarkerTone, L.CircleMarkerOptions> = {
  plain: { radius: 9, color: "#08775b", weight: 3, fillColor: "#08775b", fillOpacity: 0.35 },
  match: { radius: 10, color: "#08775b", weight: 3, fillColor: "#16a37b", fillOpacity: 0.7 },
  other: { radius: 6, color: "#8a96a5", weight: 2, fillColor: "#8a96a5", fillOpacity: 0.25 },
};

/**
 * Circle markers rather than Leaflet's default pin: the default icon is loaded
 * from image files whose bundled paths break under Vite.
 */
export function institutionMarker(
  latitude: number,
  longitude: number,
  tone: MarkerTone = "plain",
): L.CircleMarker {
  return L.circleMarker([latitude, longitude], MARKER_STYLE[tone]);
}

export function viewerMarker(latitude: number, longitude: number): L.CircleMarker {
  return L.circleMarker([latitude, longitude], {
    radius: 10,
    color: "#b5741a",
    weight: 3,
    fillColor: "#e2a84a",
    fillOpacity: 0.55,
  });
}

/**
 * Build a popup as DOM rather than markup.
 *
 * Leaflet assigns string popup content with innerHTML, so a name carrying
 * markup would run as script. Institution names come from an open write
 * endpoint, so they are set with textContent and never parsed as HTML.
 */
export function popupNode(title: string, note?: string): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "map-popup";
  const name = document.createElement("strong");
  name.textContent = title;
  wrapper.append(name);
  if (note) {
    const detail = document.createElement("small");
    detail.textContent = note;
    wrapper.append(detail);
  }
  return wrapper;
}
