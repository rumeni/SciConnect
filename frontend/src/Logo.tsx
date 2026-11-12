import { useT } from "./i18n";

/**
 * The SciConnect logo.
 *
 * Files are served from this site (`frontend/public/brand/`), which the page's
 * Content-Security-Policy requires. The full logo is the horizontal lockup —
 * navy psi under three linked orange dots, a divider, then "Sci" in navy and
 * "Connect" in orange — on a transparent background, so it sits in one row
 * with the header buttons.
 *
 * `BrandMark` is the app icon (white psi and orange dots on a navy square), the
 * same picture as the favicon, for places too narrow for the wordmark.
 */
export function BrandMark({ className = "brand-mark" }: { className?: string }) {
  return (
    <img
      className={className}
      src="/brand/sciconnect-mark.png"
      alt="SciConnect"
      width={256}
      height={256}
    />
  );
}

/**
 * The full logo.
 *
 * It is also the way home, as visitors expect a site's logo to be. It is a real
 * link to "/", so it can be opened in a new tab, but a plain click is handed to
 * `onHome` and the app moves without reloading.
 */
export function Brand({ onHome }: { onHome: () => void }) {
  const t = useT();
  return (
    <a
      className="brand brand-link"
      href="/"
      aria-label={t("brand.home")}
      onClick={(event) => {
        // Ctrl/Cmd/Shift-click and middle-click keep their usual meaning.
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return;
        event.preventDefault();
        onHome();
      }}
    >
      <img
        className="brand-logo"
        src="/brand/sciconnect-logo.png"
        alt={t("brand.alt")}
        width={800}
        height={203}
      />
    </a>
  );
}
