import { useT } from "./i18n";
import { LanguageSwitch } from "./LanguageSwitch";
import { Brand } from "./Logo";
import { PARTNER_GROUPS, type Partner } from "./partnerList";

/**
 * Who backs SciConnect. A plain page reached from the start page.
 *
 * A group with no members is left out, and with nobody listed at all the page
 * says the list is on its way rather than showing empty headings.
 */
export function Partners({
  onHome,
  onContact,
}: {
  onHome: () => void;
  onContact: () => void;
}) {
  const t = useT();
  const groups = PARTNER_GROUPS.filter((group) => group.members.length > 0);

  return (
    <main className="partners">
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
          <a
            className="primary contact-link"
            href="/kontakt"
            onClick={(event) => {
              event.preventDefault();
              onContact();
            }}
          >
            {t("landing.contact")}
          </a>
        </div>
      </header>

      <section className="partners-intro">
        <h1 className="landing-title">{t("partners.title")}</h1>
        <p className="landing-lede">{t("partners.lede")}</p>
      </section>

      {groups.length === 0 ? (
        <p className="partners-empty">{t("partners.empty")}</p>
      ) : (
        groups.map((group) => (
          <section className="partner-group" key={group.title}>
            <h2>{t(group.title)}</h2>
            <p className="section-hint">{t(group.hint)}</p>
            <ul className="partner-list">
              {group.members.map((partner) => (
                <li key={partner.name}>
                  <PartnerCard partner={partner} />
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </main>
  );
}

function PartnerCard({ partner }: { partner: Partner }) {
  const body = (
    <>
      {partner.logo ? (
        <img className="partner-logo" src={partner.logo} alt="" loading="lazy" />
      ) : (
        <span className="partner-initial" aria-hidden="true">
          {partner.name.charAt(0)}
        </span>
      )}
      <span className="partner-name">{partner.name}</span>
      {partner.description && <span className="partner-note">{partner.description}</span>}
    </>
  );

  // Their site opens in a new tab. noopener keeps the new page from steering
  // this one through window.opener; noreferrer sends them nothing about it.
  return partner.url ? (
    <a className="partner-card" href={partner.url} target="_blank" rel="noopener noreferrer">
      {body}
    </a>
  ) : (
    <div className="partner-card">{body}</div>
  );
}
