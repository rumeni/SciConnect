import { useState } from "react";
import { api } from "./api";
import { useT } from "./i18n";
import { LanguageSwitch } from "./LanguageSwitch";
import { BrandMark } from "./Logo";
import { enterAsAdmin } from "./session";

/**
 * Where an admin enters their key.
 *
 * The key is checked with the server before it is kept, so a wrong one never
 * becomes this tab's session. Each attempt counts against a small per-address
 * allowance on the server, which is what makes guessing pointless; this screen
 * only reports the wait.
 */
export function SignIn({
  expired,
  onBack,
  onSignedIn,
}: {
  expired: boolean;
  onBack: () => void;
  onSignedIn: () => void;
}) {
  const t = useT();
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  /**
   * What went wrong, as a key rather than a sentence, so the message follows
   * the language if it is switched while the error is on screen. A refusal
   * from the server is already a sentence and is kept as one.
   */
  const [error, setError] = useState<{ key?: Parameters<typeof t>[0]; text?: string } | null>(
    expired ? { key: "signIn.expired" } : null,
  );

  const message = error ? (error.key ? t(error.key) : error.text) : "";

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.checkAdminKey(key);
      enterAsAdmin(key);
      onSignedIn();
    } catch (reason) {
      setError(
        reason instanceof TypeError
          ? { key: "signIn.unreachable" }
          : reason instanceof Error
            ? { text: reason.message }
            : { key: "signIn.failed" },
      );
      setBusy(false);
    }
  };

  return (
    <main className="sign-in">
      <form
        className="sign-in-card"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <BrandMark className="sign-in-mark" />
        <h1>{t("signIn.title")}</h1>
        <p className="sign-in-hint">{t("signIn.hint")}</p>

        {/* Lets a password manager file the key under a name and offer it next time. */}
        <input
          type="text"
          name="username"
          value="admin"
          autoComplete="username"
          readOnly
          hidden
        />

        <label htmlFor="admin-key">{t("signIn.keyLabel")}</label>
        <input
          id="admin-key"
          name="password"
          type="password"
          value={key}
          autoComplete="current-password"
          spellCheck={false}
          autoFocus
          required
          aria-invalid={message ? true : undefined}
          aria-describedby={message ? "sign-in-error" : undefined}
          onChange={(event) => setKey(event.target.value)}
        />

        {message && (
          <p id="sign-in-error" className="form-error" role="alert">
            {message}
          </p>
        )}

        <div className="sign-in-actions">
          <button type="submit" className="primary" disabled={busy || key.trim() === ""}>
            {busy ? t("signIn.checking") : t("signIn.submit")}
          </button>
          <button type="button" className="link-button" onClick={onBack}>
            {t("common.back")}
          </button>
        </div>

        <p className="sign-in-note">{t("signIn.note")}</p>
        <LanguageSwitch className="sign-in-lang" />
      </form>
    </main>
  );
}
