import { useRef, useState } from "react";
import { useT, type MessageKey, type Translate } from "./i18n";
import { LanguageSwitch } from "./LanguageSwitch";
import { Brand } from "./Logo";

/**
 * The start page: what SciConnect is, and the way in.
 *
 * Its centre is the catalog's own model drawn as a graph. Each example question
 * lights the records and links it has to cross, which is the idea the rest of
 * the app is built on: a match is a chain of stated links, not a keyword.
 */
export function Landing({
  onGuest,
  onAdmin,
  onPartners,
  onContact,
}: {
  onGuest: () => void;
  onAdmin: () => void;
  onPartners: () => void;
  onContact: () => void;
}) {
  const t = useT();
  const tryIt = useRef<HTMLElement>(null);

  return (
    <main className="landing">
      <header className="landing-head">
        <Brand
          onHome={() => {
            // Already home: the logo just brings the top of the page back.
            const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
            window.scrollTo({ top: 0, behavior: still ? "auto" : "smooth" });
          }}
        />
        <div className="head-actions">
          <LanguageSwitch />
          <a
            className="secondary partners-link"
            href="/partners"
            onClick={(event) => {
              event.preventDefault();
              onPartners();
            }}
          >
            {t("landing.partners")}
          </a>
          <a
            className="primary contact-link"
            href="/kontakt"
            onClick={(event) => {
              event.preventDefault();
              onContact();
            }}
          >
            {t("landing.contact")}
          </a>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-intro">
          <h1 className="landing-title">{t("landing.title")}</h1>
          <p className="landing-lede">{t("landing.lede")}</p>
          <button
            type="button"
            className="primary landing-cta"
            onClick={() => {
              const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
              tryIt.current?.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" });
              tryIt.current?.focus({ preventScroll: true });
            }}
          >
            {t("landing.cta")}
          </button>
        </div>

        <CapabilityGraph />
      </section>

      <section className="landing-why">
        <h2>{t("landing.whyTitle")}</h2>
        <div className="landing-why-text">
          <p>{t("landing.why1")}</p>
          <p>{t("landing.why2")}</p>
        </div>
      </section>

      <section className="landing-try" id="try" ref={tryIt} tabIndex={-1} aria-labelledby="try-title">
        <h2 id="try-title">{t("landing.tryTitle")}</h2>
        <div className="landing-choices">
          <div className="choice choice-guest">
            <h3>{t("landing.guestTitle")}</h3>
            <p>{t("landing.guestText")}</p>
            <button type="button" className="primary" onClick={onGuest}>
              {t("landing.guestButton")}
            </button>
          </div>
          <div className="choice choice-admin">
            <h3>{t("landing.adminTitle")}</h3>
            <p>{t("landing.adminText")}</p>
            <button type="button" className="secondary" onClick={onAdmin}>
              {t("landing.adminButton")}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}

type NodeId = "institution" | "instrument" | "analysis" | "researcher" | "microorganism";

const NODES: Record<NodeId, { x: number; y: number; label: MessageKey; labelAbove?: boolean }> = {
  institution: { x: 74, y: 176, label: "graph.node.institution" },
  instrument: { x: 270, y: 62, label: "graph.node.instrument", labelAbove: true },
  analysis: { x: 336, y: 176, label: "graph.node.analysis" },
  researcher: { x: 270, y: 290, label: "graph.node.researcher" },
  microorganism: { x: 470, y: 176, label: "graph.node.microorganism" },
};

type EdgeId = "owns" | "offers" | "employs" | "uses" | "runs" | "targets";

const EDGES: Record<EdgeId, { from: NodeId; to: NodeId; label: MessageKey }> = {
  owns: { from: "institution", to: "instrument", label: "graph.edge.owns" },
  offers: { from: "institution", to: "analysis", label: "graph.edge.offers" },
  employs: { from: "institution", to: "researcher", label: "graph.edge.employs" },
  uses: { from: "analysis", to: "instrument", label: "graph.edge.uses" },
  runs: { from: "analysis", to: "researcher", label: "graph.edge.runs" },
  targets: { from: "analysis", to: "microorganism", label: "graph.edge.targets" },
};

const QUESTIONS: { text: MessageKey; why: MessageKey; nodes: NodeId[]; edges: EdgeId[] }[] = [
  {
    text: "graph.q1",
    why: "graph.q1.why",
    nodes: ["institution", "instrument"],
    edges: ["owns"],
  },
  {
    text: "graph.q2",
    why: "graph.q2.why",
    nodes: ["institution", "analysis", "microorganism"],
    edges: ["offers", "targets"],
  },
  {
    text: "graph.q3",
    why: "graph.q3.why",
    nodes: ["analysis", "instrument", "researcher"],
    edges: ["uses", "runs"],
  },
  {
    text: "graph.q4",
    why: "graph.q4.why",
    nodes: ["institution", "instrument", "analysis", "researcher", "microorganism"],
    edges: ["owns", "offers", "employs", "uses", "runs", "targets"],
  },
];

/** One edge spelled out for a screen reader: "Institution owns Instrument". */
const edgeSentence = (t: Translate, id: EdgeId) =>
  `${t(NODES[EDGES[id].from].label)} ${t(EDGES[id].label)} ${t(NODES[EDGES[id].to].label)}`;

function CapabilityGraph() {
  const t = useT();
  const [chosen, setChosen] = useState(QUESTIONS.length - 1);
  const question = QUESTIONS[chosen];
  const lit = new Set<string>([...question.nodes, ...question.edges]);

  return (
    <figure className="capability-graph">
      <svg
        viewBox="0 0 544 340"
        role="img"
        aria-label={`${t(question.text)} ${t("graph.linksInvolved")}: ${question.edges
          .map((id) => edgeSentence(t, id))
          .join(", ")}.`}
      >
        {(Object.keys(EDGES) as EdgeId[]).map((id) => {
          const { from, to, label } = EDGES[id];
          const a = NODES[from];
          const b = NODES[to];
          return (
            <g key={id} className={lit.has(id) ? "edge lit" : "edge"}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
              <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 6} textAnchor="middle">
                {t(label)}
              </text>
            </g>
          );
        })}
        {(Object.keys(NODES) as NodeId[]).map((id) => {
          const node = NODES[id];
          return (
            <g key={id} className={lit.has(id) ? "node lit" : "node"}>
              <circle cx={node.x} cy={node.y} r={15} />
              <text
                x={node.x}
                y={node.labelAbove ? node.y - 26 : node.y + 36}
                textAnchor="middle"
              >
                {t(node.label)}
              </text>
            </g>
          );
        })}
      </svg>

      <figcaption>
        <ul className="graph-questions" aria-label={t("graph.questions")}>
          {QUESTIONS.map((item, index) => (
            <li key={item.text}>
              <button
                type="button"
                aria-pressed={index === chosen}
                className={index === chosen ? "graph-question chosen" : "graph-question"}
                onClick={() => setChosen(index)}
              >
                {t(item.text)}
              </button>
            </li>
          ))}
        </ul>
        <p className="graph-why" aria-live="polite">
          {t(question.why)}
        </p>
      </figcaption>
    </figure>
  );
}
