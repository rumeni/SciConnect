import { useEffect, useState, useSyncExternalStore } from "react";
import { Landing } from "./Landing";
import { Partners } from "./Partners";
import { enterAsGuest, leave, session, watchSession, type Role } from "./session";
import { SignIn } from "./SignIn";
import { Workspace } from "./Workspace";

const PARTNERS_PATH = "/partners";

/** The address bar's path, kept in step with Back and Forward. */
function usePath(): [string, (next: string) => void] {
  const [path, setPath] = useState(() => window.location.pathname);
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  const go = (next: string) => {
    if (next !== window.location.pathname) window.history.pushState(null, "", next);
    setPath(next);
  };
  return [path, go];
}

/**
 * Which screen this tab shows: the start page, the admin sign-in, the
 * partners page, or the app.
 *
 * Once someone has picked guest or admin, a reload returns them to the app
 * rather than the start page, until the tab is closed or they leave.
 */
export default function App() {
  const current = useSyncExternalStore(watchSession, session);
  // The partners page has an address of its own so it can be linked to. It is
  // public and reads nothing, so it is shown whoever is signed in.
  const [path, go] = usePath();
  // Where "Back" on the sign-in screen returns to: a guest who chose to sign in
  // goes back to browsing, everyone else to the start page.
  const [signingInFrom, setSigningInFrom] = useState<Role | "start" | null>(null);

  const screen =
    path.replace(/\/+$/, "") === PARTNERS_PATH
      ? "partners"
      : current.role
        ? "workspace"
        : signingInFrom || current.expired
          ? "sign-in"
          : "start";

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [screen]);

  if (screen === "partners") {
    return <Partners onHome={() => go("/")} />;
  }

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

  return (
    <Landing
      onGuest={enterAsGuest}
      onAdmin={() => setSigningInFrom("start")}
      onPartners={() => go(PARTNERS_PATH)}
    />
  );
}
