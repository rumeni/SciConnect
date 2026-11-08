import { getLang, translate, type Translate } from "./i18n";
import type { InstitutionMapPoint, ViewerLocation } from "./types";

const PLACE_KEY = "sciconnect.viewer-location";
const ASKED_KEY = "sciconnect.location-asked";

/**
 * The visitor's position is kept in their own browser and is never sent to the
 * API. Only an address they choose to type is looked up on the server.
 */
export function readStoredLocation(): ViewerLocation | null {
  try {
    const raw = localStorage.getItem(PLACE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ViewerLocation;
    if (typeof parsed?.latitude !== "number" || typeof parsed?.longitude !== "number") {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function storeLocation(location: ViewerLocation): void {
  try {
    localStorage.setItem(PLACE_KEY, JSON.stringify(location));
  } catch {
    /* A browser that refuses storage still works, it just forgets. */
  }
}

export function forgetLocation(): void {
  try {
    localStorage.removeItem(PLACE_KEY);
  } catch {
    /* nothing to clean up */
  }
}

export function hasBeenAsked(): boolean {
  try {
    return localStorage.getItem(ASKED_KEY) === "yes";
  } catch {
    // Without storage the prompt would reappear on every load, which is worse
    // than never volunteering it.
    return true;
  }
}

export function rememberAsked(): void {
  try {
    localStorage.setItem(ASKED_KEY, "yes");
  } catch {
    /* the prompt simply gets offered again next time */
  }
}

/** Ask the browser for the device position. Requires a user gesture to be useful. */
export function requestDeviceLocation(): Promise<ViewerLocation> {
  const say = (key: Parameters<typeof translate>[1]) => translate(getLang(), key);
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error(say("nearby.noGeolocation")));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          // Stored, so it is written in whichever language was in use. It is
          // never shown: `placeName` translates it afresh on every render.
          label: say("nearby.deviceLabel"),
          source: "device",
        }),
      (error) =>
        reject(
          new Error(
            error.code === error.PERMISSION_DENIED
              ? say("nearby.denied")
              : say("nearby.unknown"),
          ),
        ),
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 },
    );
  });
}

/**
 * What to call the point distances are measured from.
 *
 * A typed address is the visitor's own words and stands as it is; the device
 * position has no name of its own, so it is named in the current language
 * rather than in the one it was shared in.
 */
export function placeName(location: ViewerLocation, t: Translate): string {
  return location.source === "device" ? t("nearby.deviceLabel") : location.label;
}

/**
 * Geocoders answer with a full postal breakdown ("1, Kneza Mihaila, Stari grad,
 * ... 11000, Serbia"). The first few parts are enough to recognise a place.
 */
export function shortenPlaceName(label: string, parts = 3): string {
  const pieces = label.split(",").map((piece) => piece.trim()).filter(Boolean);
  return pieces.slice(0, parts).join(", ") || label;
}

const EARTH_RADIUS_KM = 6371;
const toRadians = (degrees: number) => (degrees * Math.PI) / 180;

/** Great-circle distance in kilometres. */
export function distanceKm(
  from: { latitude: number; longitude: number },
  to: { latitude: number; longitude: number },
): number {
  const dLat = toRadians(to.latitude - from.latitude);
  const dLon = toRadians(to.longitude - from.longitude);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(from.latitude)) *
      Math.cos(toRadians(to.latitude)) *
      Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(a));
}

export type NearbyInstitution = InstitutionMapPoint & { distanceKm: number };

export function sortByDistance(
  points: InstitutionMapPoint[],
  origin: ViewerLocation,
): NearbyInstitution[] {
  return points
    .map((point) => ({ ...point, distanceKm: distanceKm(origin, point) }))
    .sort((left, right) => left.distanceKm - right.distanceKm);
}

export function formatDistance(km: number, t: Translate): string {
  if (km < 1) return t("nearby.metres", { value: Math.round(km * 1000) });
  if (km < 10) return t("nearby.kilometres", { value: km.toFixed(1) });
  return t("nearby.kilometres", { value: Math.round(km) });
}
