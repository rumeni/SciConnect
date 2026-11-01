/**
 * The organizations shown on the Partners & Supporters page.
 *
 * To add one, put an entry in the right group below. A logo is optional: drop
 * the image into `frontend/public/partners/` and name it here as
 * "/partners/<file>". Logos must be served from this site, because the page's
 * Content-Security-Policy refuses images from other hosts. SVG or a PNG about
 * 400px wide on a transparent background works best on both themes.
 *
 * Example:
 *
 *   {
 *     name: "Institute of Example Sciences",
 *     url: "https://example.org",
 *     logo: "/partners/example.svg",
 *     description: "Hosts the shared sequencing facility.",
 *   },
 */

export type Partner = {
  name: string;
  /** Their own site. Opens in a new tab. */
  url?: string;
  /** A path under /partners/, served from this site. */
  logo?: string;
  /** One sentence on what they contribute. */
  description?: string;
};

export type PartnerGroup = {
  title: string;
  /** What being in this group means, in a sentence. */
  hint: string;
  members: Partner[];
};

export const PARTNER_GROUPS: PartnerGroup[] = [
  {
    title: "Partners",
    hint: "Institutions that contribute data, expertise or infrastructure to SciConnect.",
    members: [],
  },
  {
    title: "Supporters",
    hint: "Organizations and people who fund or otherwise help the project grow.",
    members: [],
  },
];
