import { useState } from "react";
import { api } from "./api";
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
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(
    expired ? "Your admin key is no longer accepted. It may have been changed. Sign in again." : "",
  );

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await api.checkAdminKey(key);
      enterAsAdmin(key);
      onSignedIn();
    } catch (reason) {
      setError(
        reason instanceof TypeError
          ? "The server could not be reached. Check your connection and try again."
          : reason instanceof Error
            ? reason.message
            : "Signing in failed.",
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
        <h1>Sign in as admin</h1>
        <p className="sign-in-hint">
          Admins can add institutions, instruments, analyses and researchers, connect them, and
          remove them. Enter the admin key you were given.
        </p>

        {/* Lets a password manager file the key under a name and offer it next time. */}
        <input
          type="text"
          name="username"
          value="admin"
          autoComplete="username"
          readOnly
          hidden
        />

        <label htmlFor="admin-key">Admin key</label>
        <input
          id="admin-key"
          name="password"
          type="password"
          value={key}
          autoComplete="current-password"
          spellCheck={false}
          autoFocus
          required
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? "sign-in-error" : undefined}
          onChange={(event) => setKey(event.target.value)}
        />

        {error && (
          <p id="sign-in-error" className="form-error" role="alert">
            {error}
          </p>
        )}

        <div className="sign-in-actions">
          <button type="submit" className="primary" disabled={busy || key.trim() === ""}>
            {busy ? "Checking…" : "Sign in"}
          </button>
          <button type="button" className="link-button" onClick={onBack}>
            Back
          </button>
        </div>

        <p className="sign-in-note">
          The key is kept only until you close this tab. Without one you can still browse
          everything as a guest.
        </p>
      </form>
    </main>
  );
}
