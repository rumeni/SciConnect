import { useEffect, useState, useSyncExternalStore } from "react";
import { Landing } from "./Landing";
import { enterAsGuest, leave, session, watchSession, type Role } from "./session";
import { SignIn } from "./SignIn";
import { Workspace } from "./Workspace";

/**
 * Which screen this tab shows: the start page, the admin sign-in, or the app.
 *
 * Once someone has picked guest or admin, a reload returns them to the app
 * rather than the start page, until the tab is closed or they leave.
 */
export default function App() {
  const current = useSyncExternalStore(watchSession, session);
  // Where "Back" on the sign-in screen returns to: a guest who chose to sign in
  // goes back to browsing, everyone else to the start page.
  const [signingInFrom, setSigningInFrom] = useState<Role | "start" | null>(null);

  const screen = current.role
    ? "workspace"
    : signingInFrom || current.expired
      ? "sign-in"
      : "start";

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [screen]);

  if (current.role) {
    return (
      <Workspace
        key={current.role}
        role={current.role}
        onSignIn={() => {
          setSigningInFrom("guest");
          leave();
        }}
        onLeave={() => {
          setSigningInFrom(null);
          leave();
        }}
      />
    );
  }

  if (screen === "sign-in") {
    return (
      <SignIn
        expired={current.expired}
        onBack={() => {
          const from = signingInFrom;
          setSigningInFrom(null);
          if (from === "guest") enterAsGuest();
          else leave();
        }}
        onSignedIn={() => setSigningInFrom(null)}
      />
    );
  }

  return <Landing onGuest={enterAsGuest} onAdmin={() => setSigningInFrom("start")} />;
}
