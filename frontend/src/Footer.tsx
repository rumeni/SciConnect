import { CONTACT_EMAIL } from "./Contact";
import { useT } from "./i18n";

/** The strip at the foot of every page: who we are, how to write to us, and the way back up. */
export function Footer() {
  const t = useT();

  /**
   * Scrolls up and takes keyboard focus along, so the next Tab starts at the
   * top of the page instead of continuing from the footer.
   */
  const toTop = () => {
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: still ? "auto" : "smooth" });
    const page = document.querySelector("main");
    if (page) {
      page.tabIndex = -1;
      page.focus({ preventScroll: true });
    }
  };

  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <span>{t("footer.tagline", { year: new Date().getFullYear() })}</span>
        <div className="site-footer-end">
          <span>
            {t("footer.contact")}{" "}
            <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
          </span>
          <button type="button" className="to-top" onClick={toTop}>
            <span aria-hidden="true">↑</span> {t("footer.toTop")}
          </button>
        </div>
      </div>
    </footer>
  );
}
