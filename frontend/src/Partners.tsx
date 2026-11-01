import { Brand } from "./Logo";
import { PARTNER_GROUPS, type Partner } from "./partnerList";

/**
 * Who backs SciConnect. A plain page reached from the start page.
 *
 * A group with no members is left out, and with nobody listed at all the page
 * says the list is on its way rather than showing empty headings.
 */
export function Partners({ onHome }: { onHome: () => void }) {
  const groups = PARTNER_GROUPS.filter((group) => group.members.length > 0);

  return (
    <main className="partners">
      <header className="landing-head">
        <Brand />
        <a
          className="link-button"
          href="/"
          onClick={(event) => {
            event.preventDefault();
            onHome();
          }}
        >
          Back to SciConnect
        </a>
      </header>

      <section className="partners-intro">
        <h1 className="landing-title">Partners &amp; Supporters</h1>
        <p className="landing-lede">
          SciConnect is built with the help of institutions and organizations that believe
          research capability should be easy to find.
        </p>
      </section>

      {groups.length === 0 ? (
        <p className="partners-empty">Our partners and supporters will be listed here soon.</p>
      ) : (
        groups.map((group) => (
          <section className="partner-group" key={group.title}>
            <h2>{group.title}</h2>
            <p className="section-hint">{group.hint}</p>
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
