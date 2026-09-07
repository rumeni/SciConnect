import { FormEvent, useState } from "react";
import { api } from "./api";
import { requestDeviceLocation, shortenPlaceName } from "./viewerLocation";
import type { ViewerLocation } from "./types";

/**
 * Asks — never assumes — whether the visitor wants to share where they are.
 *
 * Two ways to answer, with different privacy costs, both spelled out in the
 * dialog: the device position stays in this browser, while a typed address is
 * sent to the API to be looked up.
 */
export function LocationPrompt({
  onShare,
  onDismiss,
}: {
  onShare: (location: ViewerLocation) => void;
  onDismiss: () => void;
}) {
  const [address, setAddress] = useState("");
  const [busy, setBusy] = useState<"device" | "address" | null>(null);
  const [error, setError] = useState("");

  const useDevice = async () => {
    setBusy("device");
    setError("");
    try {
      onShare(await requestDeviceLocation());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not read your location.");
    } finally {
      setBusy(null);
    }
  };

  const useAddress = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("address");
    setError("");
    try {
      const found = await api.geocode(address);
      onShare({
        latitude: found.latitude,
        longitude: found.longitude,
        label: shortenPlaceName(found.label),
        source: "address",
      });
    } catch {
      setError("That address could not be found. Try adding the city or country.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="detail-backdrop" onClick={onDismiss} role="presentation">
      <div
        className="prompt"
        role="dialog"
        aria-modal="true"
        aria-labelledby="location-prompt-title"
        onClick={(event) => event.stopPropagation()}
      >
        <p className="eyebrow">Institutions near you</p>
        <h2 id="location-prompt-title">Share where you are?</h2>
        <p className="prompt-intro">
          If you share a location, the institutions in the catalogue are shown on a map
          around it, nearest first. You can search the whole catalogue without sharing
          anything.
        </p>

        <div className="prompt-choice">
          <button
            type="button"
            className="primary"
            onClick={() => void useDevice()}
            disabled={busy !== null}
          >
            {busy === "device" ? "Waiting for your browser…" : "Use my device location"}
          </button>
          <small>
            Your browser will ask for permission. The position stays in this browser and is
            never sent to the server.
          </small>
        </div>

        <form className="prompt-choice" onSubmit={useAddress}>
          <label>
            <span>Or enter an address</span>
            <input
              type="text"
              value={address}
              placeholder="Knez Mihailova 1, Belgrade"
              onChange={(event) => setAddress(event.target.value)}
            />
          </label>
          <button
            type="submit"
            className="secondary"
            disabled={busy !== null || address.trim().length < 3}
          >
            {busy === "address" ? "Looking it up…" : "Use this address"}
          </button>
          <small>
            The address you type is sent to the server to be looked up on OpenStreetMap.
          </small>
        </form>

        {error && <p className="error">{error}</p>}

        <div className="prompt-footer">
          <button type="button" className="link-button" onClick={onDismiss}>
            No thanks
          </button>
          <small>You can change this later from the “Near me” tab.</small>
        </div>
      </div>
    </div>
  );
}
