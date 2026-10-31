/**
 * Who this browser is using the app as: nobody yet, a guest, or an admin.
 *
 * The role here only decides what the page shows. It grants nothing: the
 * server checks the admin key on every request that changes data, so a guest
 * who edits this state in the console gets forms that the API refuses.
 *
 * Kept in `sessionStorage`, not `localStorage`: closing the tab forgets the
 * key, so a shared or public machine does not keep write access after the
 * person who signed in walks away. A memory copy backs it up, because private
 * browsing can refuse storage entirely.
 */

export type Role = "guest" | "admin";

export type Session = {
  role: Role | null;
  /** The admin key, empty unless `role` is admin. */
  key: string;
  /** Set when the server stopped accepting the key mid-session, say after it was changed. */
  expired: boolean;
};

const KEY_ITEM = "sciconnect.adminKey";
const GUEST_ITEM = "sciconnect.guest";

let current: Session = load();
const listeners = new Set<() => void>();

function load(): Session {
  const key = readItem(KEY_ITEM);
  if (key) return { role: "admin", key, expired: false };
  return { role: readItem(GUEST_ITEM) ? "guest" : null, key: "", expired: false };
}

function readItem(name: string): string {
  try {
    return window.sessionStorage.getItem(name) ?? "";
  } catch {
    return "";
  }
}

function writeItem(name: string, value: string): void {
  try {
    if (value) window.sessionStorage.setItem(name, value);
    else window.sessionStorage.removeItem(name);
  } catch {
    /* The memory copy is the whole story. */
  }
}

function update(next: Session): void {
  current = next;
  writeItem(KEY_ITEM, next.role === "admin" ? next.key : "");
  writeItem(GUEST_ITEM, next.role === "guest" ? "1" : "");
  listeners.forEach((notify) => notify());
}

export function session(): Session {
  return current;
}

export function adminKey(): string {
  return current.role === "admin" ? current.key : "";
}

export function enterAsGuest(): void {
  update({ role: "guest", key: "", expired: false });
}

/** Called only once the server has confirmed the key. */
export function enterAsAdmin(key: string): void {
  update({ role: "admin", key: key.trim(), expired: false });
}

/** Back to the start page, forgetting the key. */
export function leave(): void {
  update({ role: null, key: "", expired: false });
}

/** The server refused a key it used to accept: sign out, and say why. */
export function expire(): void {
  if (current.role !== "admin") return;
  update({ role: null, key: "", expired: true });
}

/** Subscribe, for `useSyncExternalStore`. */
export function watchSession(notify: () => void): () => void {
  listeners.add(notify);
  return () => listeners.delete(notify);
}
