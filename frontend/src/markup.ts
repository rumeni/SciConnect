/**
 * The two marks start-page texts may carry: `**bold**` and `__species name__`,
 * each only as a closed pair and never one inside the other. A lone `**` or
 * `__`, or a single `_` as in snake_case, stays literal text. Species names
 * are Latin and written in italics by convention.
 */
const MARKUP = /\*\*(.+?)\*\*|__(.+?)__/g;

export type Segment = { kind: "text" | "bold" | "species"; text: string };

/** Splits a translated sentence into its marked and unmarked runs, in order. */
export function segments(text: string): Segment[] {
  const found: Segment[] = [];
  let last = 0;
  for (const match of text.matchAll(MARKUP)) {
    const at = match.index ?? 0;
    if (at > last) found.push({ kind: "text", text: text.slice(last, at) });
    found.push(
      match[1] !== undefined
        ? { kind: "bold", text: match[1] }
        : { kind: "species", text: match[2] },
    );
    last = at + match[0].length;
  }
  if (last < text.length) found.push({ kind: "text", text: text.slice(last) });
  return found;
}

/** The same sentence with its marks removed, for labels that cannot hold markup. */
export function plain(text: string): string {
  return segments(text)
    .map((part) => part.text)
    .join("");
}
