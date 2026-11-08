/**
 * The organizations shown on the Partners & Sponsors page.
 *
 * To add one, put an entry in the right group below. A logo is optional: drop
 * the image into `frontend/public/partner-logos/` and name it here as
 * "/partner-logos/<file>". Logos must be served from this site, because the page's
 * Content-Security-Policy refuses images from other hosts. SVG or a PNG about
 * 400px wide on a transparent background works best on both themes.
 *
 * Example:
 *
 *   {
 *     name: "Institute of Example Sciences",
 *     url: "https://example.org",
 *     logo: "/partner-logos/example.svg",
 *     description: "Hosts the shared sequencing facility.",
 *   },
 */

import type { MessageKey } from "./i18n";

export type Partner = {
  name: string;
  /** Their own site. Opens in a new tab. */
  url?: string;
  /** A path under /partner-logos/, served from this site. */
  logo?: string;
  /** One sentence on what they contribute. */
  description?: string;
};

export type PartnerGroup = {
  /** Translation key for the heading; the text lives in `i18n.ts`. */
  title: MessageKey;
  /** Translation key for what being in this group means, in a sentence. */
  hint: MessageKey;
  members: Partner[];
};

export const PARTNER_GROUPS: PartnerGroup[] = [
  {
    title: "partners.group.partners",
    hint: "partners.group.partners.hint",
    members: [],
  },
  {
    title: "partners.group.sponsors",
    hint: "partners.group.sponsors.hint",
    members: [],
  },
];
