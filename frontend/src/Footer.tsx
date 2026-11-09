import { CONTACT_EMAIL } from "./Contact";
import { useT } from "./i18n";

/** The strip at the foot of every page: who we are and how to write to us. */
export function Footer() {
  const t = useT();
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <span>{t("footer.tagline", { year: new Date().getFullYear() })}</span>
        <span>
          {t("footer.contact")}{" "}
          <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
        </span>
      </div>
    </footer>
  );
}
