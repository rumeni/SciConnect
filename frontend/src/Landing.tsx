import { useRef, useState } from "react";
import { Brand } from "./Logo";

/**
 * The start page: what SciConnect is, and the way in.
 *
 * Its centre is the catalog's own model drawn as a graph. Each example question
 * lights the records and links it has to cross, which is the idea the rest of
 * the app is built on: a match is a chain of stated links, not a keyword.
 */
export function Landing({ onGuest, onAdmin }: { onGuest: () => void; onAdmin: () => void }) {
  const tryIt = useRef<HTMLElement>(null);

  return (
    <main className="landing">
      <Brand />

      <section className="landing-hero">
        <div className="landing-intro">
          <h1 className="landing-title">Find the lab that can run your analysis.</h1>
          <p className="landing-lede">
            SciConnect records which institutions own which instruments, which analyses they
            offer on them, who performs those analyses, and which microorganisms they target. Ask
            for the exact combination your work needs and get the places that have all of it.
          </p>
          <button
            type="button"
            className="primary landing-cta"
            onClick={() => {
              const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
              tryIt.current?.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" });
              tryIt.current?.focus({ preventScroll: true });
            }}
          >
            Try it
          </button>
        </div>

        <CapabilityGraph />
      </section>

      <section className="landing-why">
        <h2>Why it exists</h2>
        <div className="landing-why-text">
          <p>
            Equipment and expertise are spread across institutes, faculties and agencies. Today
            the usual way to find a sequencer, a PCR platform or someone who works with a given
            pathogen is to know someone who knows.
          </p>
          <p>
            SciConnect writes those connections down. A researcher looking for a partner, a
            company that needs a test run, or a lab manager planning shared equipment can look
            it up instead of asking around.
          </p>
        </div>
      </section>

      <section className="landing-try" id="try" ref={tryIt} tabIndex={-1} aria-labelledby="try-title">
        <h2 id="try-title">Try it</h2>
        <div className="landing-choices">
          <div className="choice choice-guest">
            <h3>Browse as a guest</h3>
            <p>
              Search capabilities, find institutions near you, and open any record. No key
              needed.
            </p>
            <button type="button" className="primary" onClick={onGuest}>
              Browse as guest
            </button>
          </div>
          <div className="choice choice-admin">
            <h3>Sign in as admin</h3>
            <p>Everything a guest can do, plus adding, connecting and removing records.</p>
            <button type="button" className="secondary" onClick={onAdmin}>
              Sign in as admin
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}

type NodeId = "institution" | "instrument" | "analysis" | "researcher" | "microorganism";

const NODES: Record<NodeId, { x: number; y: number; label: string; labelAbove?: boolean }> = {
  institution: { x: 74, y: 176, label: "Institution" },
  instrument: { x: 270, y: 62, label: "Instrument", labelAbove: true },
  analysis: { x: 336, y: 176, label: "Analysis" },
  researcher: { x: 270, y: 290, label: "Researcher" },
  microorganism: { x: 470, y: 176, label: "Microorganism" },
};

type EdgeId = "owns" | "offers" | "employs" | "uses" | "runs" | "targets";

const EDGES: Record<EdgeId, { from: NodeId; to: NodeId; label: string }> = {
  owns: { from: "institution", to: "instrument", label: "owns" },
  offers: { from: "institution", to: "analysis", label: "offers" },
  employs: { from: "institution", to: "researcher", label: "employs" },
  uses: { from: "analysis", to: "instrument", label: "uses" },
  runs: { from: "analysis", to: "researcher", label: "run by" },
  targets: { from: "analysis", to: "microorganism", label: "targets" },
};

const QUESTIONS: { text: string; why: string; nodes: NodeId[]; edges: EdgeId[] }[] = [
  {
    text: "Which institutions have a Real-Time PCR System?",
    why: "Only instruments an institution actually owns count.",
    nodes: ["institution", "instrument"],
    edges: ["owns"],
  },
  {
    text: "Who offers Whole Genome Sequencing for Listeria monocytogenes?",
    why: "The analysis has to be stated to target that organism.",
    nodes: ["institution", "analysis", "microorganism"],
    edges: ["offers", "targets"],
  },
  {
    text: "Who runs this analysis, and on which instrument?",
    why: "The instrument and the researcher must belong to the same institution as the analysis.",
    nodes: ["analysis", "instrument", "researcher"],
    edges: ["uses", "runs"],
  },
  {
    text: "All five at once",
    why: "Every link has to hold together, inside one institution.",
    nodes: ["institution", "instrument", "analysis", "researcher", "microorganism"],
    edges: ["owns", "offers", "employs", "uses", "runs", "targets"],
  },
];

function CapabilityGraph() {
  const [chosen, setChosen] = useState(QUESTIONS.length - 1);
  const question = QUESTIONS[chosen];
  const lit = new Set<string>([...question.nodes, ...question.edges]);

  return (
    <figure className="capability-graph">
      <svg
        viewBox="0 0 544 340"
        role="img"
        aria-label={`${question.text} Links involved: ${question.edges
          .map((id) => `${NODES[EDGES[id].from].label} ${EDGES[id].label} ${NODES[EDGES[id].to].label}`)
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
                {label}
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
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>

      <figcaption>
        <ul className="graph-questions" aria-label="Example questions">
          {QUESTIONS.map((item, index) => (
            <li key={item.text}>
              <button
                type="button"
                aria-pressed={index === chosen}
                className={index === chosen ? "graph-question chosen" : "graph-question"}
                onClick={() => setChosen(index)}
              >
                {item.text}
              </button>
            </li>
          ))}
        </ul>
        <p className="graph-why" aria-live="polite">
          {question.why}
        </p>
      </figcaption>
    </figure>
  );
}
