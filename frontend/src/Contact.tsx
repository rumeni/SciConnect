import { useT } from "./i18n";
import { LanguageSwitch } from "./LanguageSwitch";
import { Brand } from "./Logo";

/** The address everything on the contact page points at. */
export const CONTACT_EMAIL = "contact@sciconnect.rs";

/**
 * How to reach the people behind SciConnect. Public, reached at /kontakt.
 *
 * Just the address, shown in full so it can be read, copied or clicked: a form
 * would need the server to send mail, and an address in plain sight is what
 * someone writing from an institution's own mail client wants anyway.
 */
export function Contact({ onHome }: { onHome: () => void }) {
  const t = useT();

  return (
    <main className="partners contact">
      <header className="landing-head">
        <Brand onHome={onHome} />
        <div className="head-actions">
          <LanguageSwitch />
          <a
            className="link-button"
            href="/"
            onClick={(event) => {
              event.preventDefault();
              onHome();
            }}
          >
            {t("partners.home")}
          </a>
        </div>
      </header>

      <section className="partners-intro">
        <h1 className="landing-title">{t("contact.title")}</h1>
        <p className="landing-lede">{t("contact.lede")}</p>
      </section>

      <section className="contact-card">
        <p className="eyebrow">{t("contact.email")}</p>
        <a className="contact-email" href={`mailto:${CONTACT_EMAIL}`}>
          {CONTACT_EMAIL}
        </a>
        <a className="primary contact-write" href={`mailto:${CONTACT_EMAIL}`}>
          {t("contact.write")}
        </a>
      </section>
    </main>
  );
}
