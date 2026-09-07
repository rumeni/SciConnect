/**
 * The SciConnect mark: a serif psi whose three heads are the brand dots.
 *
 * Drawn inline rather than loaded as two image files so it themes itself. The
 * psi is painted with `currentColor`, so it is white on the dark brand ground
 * and navy on the light one, while the dots always take the accent blue.
 */
export function BrandMark({ className = "brand-mark" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 100 100"
      role="img"
      aria-label="SciConnect"
      focusable="false"
    >
      {/* Outer arms, drawn first so the stem and serifs sit over them. */}
      <g fill="none" stroke="currentColor" strokeWidth="9.5">
        <path d="M21 34 C21 64, 23 75, 45 79" />
        <path d="M79 34 C79 64, 77 75, 55 79" />
      </g>
      <g fill="currentColor">
        {/* Serif caps on each arm, the central stem, and its foot. */}
        <rect x="11" y="29" width="20" height="5.5" rx="1.5" />
        <rect x="69" y="29" width="20" height="5.5" rx="1.5" />
        <rect x="45.25" y="29" width="9.5" height="58" />
        <rect x="36" y="29" width="28" height="5.5" rx="1.5" />
        <rect x="34" y="83" width="32" height="5.5" rx="1.5" />
      </g>
      <g className="mark-dots">
        <circle cx="21" cy="15" r="10.5" />
        <circle cx="50" cy="15" r="10.5" />
        <circle cx="79" cy="15" r="10.5" />
      </g>
    </svg>
  );
}

/** The mark with the wordmark beside it, as it appears on the stand banners. */
export function Brand() {
  return (
    <div className="brand">
      <BrandMark />
      <div className="brand-text">
        <h1 className="brand-name">
          Sci<span>Connect</span>
        </h1>
        <p className="brand-tagline">
          <span>People</span>
          <span>Science</span>
          <span>Connection</span>
        </p>
      </div>
    </div>
  );
}
