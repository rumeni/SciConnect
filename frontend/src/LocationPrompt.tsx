import { FormEvent, useRef, useState } from "react";
import { api } from "./api";
import { useT } from "./i18n";
import { useDialog } from "./useDialog";
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
  const t = useT();
  const [address, setAddress] = useState("");
  const [busy, setBusy] = useState<"device" | "address" | null>(null);
  const [error, setError] = useState("");
  const dialog = useRef<HTMLDivElement>(null);
  useDialog(true, dialog);

  const useDevice = async () => {
    setBusy("device");
    setError("");
    try {
      onShare(await requestDeviceLocation());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("prompt.readFailed"));
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
      setError(t("prompt.notFound"));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="detail-backdrop" onClick={onDismiss} role="presentation">
      <div
        ref={dialog}
        className="prompt"
        role="dialog"
        aria-modal="true"
        aria-labelledby="location-prompt-title"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <p className="eyebrow">{t("prompt.eyebrow")}</p>
        <h2 id="location-prompt-title">{t("prompt.title")}</h2>
        <p className="prompt-intro">{t("prompt.intro")}</p>

        <div className="prompt-choice">
          <button
            type="button"
            className="primary"
            onClick={() => void useDevice()}
            disabled={busy !== null}
          >
            {busy === "device" ? t("prompt.waiting") : t("prompt.useDevice")}
          </button>
          <small>{t("prompt.deviceNote")}</small>
        </div>

        <form className="prompt-choice" onSubmit={useAddress}>
          <label>
            <span>{t("prompt.addressLabel")}</span>
            <input
              type="text"
              value={address}
              placeholder={t("prompt.addressPlaceholder")}
              onChange={(event) => setAddress(event.target.value)}
            />
          </label>
          <button
            type="submit"
            className="secondary"
            disabled={busy !== null || address.trim().length < 3}
          >
            {busy === "address" ? t("prompt.lookingUp") : t("prompt.useAddress")}
          </button>
          <small>{t("prompt.addressNote")}</small>
        </form>

        {error && <p className="error">{error}</p>}

        <div className="prompt-footer">
          <button type="button" className="link-button" onClick={onDismiss}>
            {t("prompt.noThanks")}
          </button>
          <small>{t("prompt.footer")}</small>
        </div>
      </div>
    </div>
  );
}
