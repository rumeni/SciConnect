import { RefObject, useEffect } from "react";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

/**
 * Make an overlay behave the way it already claims to.
 *
 * A dialog that declares `aria-modal` but leaves focus outside it is a trap for
 * keyboard users: Tab walks away into the page behind the overlay, which they
 * cannot see. This moves focus in when the dialog opens, keeps Tab inside it,
 * and hands focus back to whatever opened it on the way out.
 */
export function useDialog(open: boolean, container: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const node = container.current;
    if (!open || !node) return;

    const opener = document.activeElement as HTMLElement | null;
    const inside = () => Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE));
    (inside()[0] ?? node).focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const reachable = inside();
      if (reachable.length === 0) {
        event.preventDefault();
        return;
      }
      const first = reachable[0];
      const last = reachable[reachable.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === first || active === node)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    node.addEventListener("keydown", onKeyDown);
    return () => {
      node.removeEventListener("keydown", onKeyDown);
      // Take focus back only when it left with the dialog. By the time this
      // runs the panel is already detached, so the focused control is gone and
      // the browser has fallen back to the body; focus deliberately moved
      // somewhere else on the page is left alone.
      const active = document.activeElement;
      const wentWithTheDialog = !active || active === document.body || node.contains(active);
      if (wentWithTheDialog) opener?.focus?.();
    };
  }, [open, container]);
}
