import { LANGUAGES, setLang, useLang, useT } from "./i18n";

/**
 * Two buttons, SR and EN, shown in every header.
 *
 * A pair of buttons rather than a dropdown: with only two languages the choice
 * and the current state are both visible without opening anything, and each
 * button is labelled with the language's own name for a reader who cannot read
 * the one currently in use.
 */
export function LanguageSwitch({ className = "" }: { className?: string }) {
  const lang = useLang();
  const t = useT();

  return (
    <div
      className={className ? `lang-switch ${className}` : "lang-switch"}
      role="group"
      aria-label={t("lang.switch")}
    >
      {LANGUAGES.map((option) => (
        <button
          key={option.code}
          type="button"
          lang={option.code}
          className={option.code === lang ? "lang-option chosen" : "lang-option"}
          aria-pressed={option.code === lang}
          title={option.label}
          onClick={() => setLang(option.code)}
        >
          {option.short}
          <span className="visually-hidden"> — {option.label}</span>
        </button>
      ))}
    </div>
  );
}
