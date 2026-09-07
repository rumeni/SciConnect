import L from "leaflet";

const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

/** Tiles are the only part of a map that needs the network. */
export function addBaseLayer(map: L.Map): void {
  L.tileLayer(TILE_URL, { maxZoom: 19, attribution: ATTRIBUTION }).addTo(map);
}

/**
 * Circle markers rather than Leaflet's default pin: the default icon is loaded
 * from image files whose bundled paths break under Vite.
 */
export function institutionMarker(latitude: number, longitude: number): L.CircleMarker {
  return L.circleMarker([latitude, longitude], {
    radius: 9,
    color: "#08775b",
    weight: 3,
    fillColor: "#08775b",
    fillOpacity: 0.35,
  });
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
