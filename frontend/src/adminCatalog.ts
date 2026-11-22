import type { Translate } from "./i18n";
import type { Institution } from "./types";

/** Show publication state wherever an admin chooses a record to edit or remove. */
export function institutionOptionLabel(item: Institution, t: Translate): string {
  if (!item.status) return item.name;
  const labels = {
    active: "status.active",
    draft: "status.draft",
    archived: "status.archived",
  } as const;
  return `${item.name} (${t(labels[item.status])})`;
}
