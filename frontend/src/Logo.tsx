import { useT } from "./i18n";

/**
 * The SciConnect logo.
 *
 * Files are served from this site (`frontend/public/brand/`), which the page's
 * Content-Security-Policy requires. The full logo has a transparent background
 * and comes in two inks; the site is light, so it uses the navy one (the white
 * ink, `sciconnect-logo-dark.webp`, is kept for dark backgrounds).
 *
 * `BrandMark` is the psi alone, for places too narrow for the wordmark.
 */
export function BrandMark({ className = "brand-mark" }: { className?: string }) {
  return (
    <img
      className={className}
      src="/brand/sciconnect-mark.png"
      alt="SciConnect"
      width={130}
      height={125}
    />
  );
}

/**
 * The full logo: the psi above the wordmark.
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
      <picture>
        <img
          className="brand-logo"
          src="/brand/sciconnect-logo.webp"
          alt={t("brand.alt")}
          width={960}
          height={887}
        />
      </picture>
    </a>
  );
}
