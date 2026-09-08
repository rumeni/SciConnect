import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import { Select } from "./form";
import type { AnalysisDetailView, Catalogs, EntityKind } from "./types";

/**
 * The connections an analysis offering currently states, each removable.
 *
 * Disconnecting leaves both records standing: the instrument is still owned,
 * the researcher still employed. Only the statement that they belong together
 * goes away, and with it the capability's searchability through that link.
 */
export function CurrentConnections({
  analysisId,
  onChanged,
}: {
  analysisId: number;
  onChanged: () => void;
}) {
  const [detail, setDetail] = useState<AnalysisDetailView | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setDetail(null);
    api
      .detail({ kind: "analysis", id: analysisId })
      .then((answer) => {
        if (active && answer.kind === "analysis") setDetail(answer.data);
      })
      .catch(() => {
        if (active) setError("Could not read this offering's connections.");
      });
    return () => {
      active = false;
    };
  }, [analysisId, version]);

  const disconnect = async (key: string, run: () => Promise<unknown>) => {
    setBusy(key);
    setError("");
    try {
      await run();
      setVersion((current) => current + 1);
      onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not disconnect");
    } finally {
      setBusy(null);
    }
  };

  if (!detail) {
    return (
      <div className="card-form">
        <h3>Current connections</h3>
        <p className="empty">{error || "Loading…"}</p>
      </div>
    );
  }

  const rows = [
    ...detail.instruments.map((item) => ({
      key: `instrument-${item.id}`,
      label: item.display_name || item.type_name,
      note: "Uses this instrument",
      run: () => api.unlinkInstrument(detail.id, item.id),
    })),
    ...detail.targets.map((item) => ({
      key: `target-${item.id}`,
      label: item.scientific_name,
      note: "Detects this organism",
      run: () => api.unlinkTarget(detail.id, item.id),
    })),
    ...detail.researchers.map((item) => ({
      key: `researcher-${item.id}`,
      label: item.full_name,
      note: item.role ? `Performed by, as ${item.role}` : "Performed by",
      run: () => api.unlinkResearcher(detail.id, item.id),
    })),
  ];

  return (
    <div className="card-form">
      <h3>Current connections</h3>
      <p className="form-hint">
        Disconnecting removes only the relationship. Both records stay in the catalogue.
      </p>
      {error && <p className="form-error">{error}</p>}
      {rows.length === 0 ? (
        <p className="empty">This offering is not connected to anything yet.</p>
      ) : (
        <ul className="link-list">
          {rows.map((row) => (
            <li key={row.key} className="connection-row">
              <span>
                <span className="link-label">{row.label}</span>
                <span className="link-note">{row.note}</span>
              </span>
              <button
                type="button"
                className="danger"
                disabled={busy !== null}
                onClick={() => void disconnect(row.key, row.run)}
              >
                {busy === row.key ? "Removing…" : "Disconnect"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

type Choice = { id: number; label: string };

/** Delete a record, after saying what will go with it. */
export function RemoveRecordForm({
  catalogs,
  onChanged,
}: {
  catalogs: Catalogs;
  onChanged: () => void;
}) {
  const [kind, setKind] = useState<EntityKind | "">("");
  const [id, setId] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [status, setStatus] = useState<{ kind: "ok" | "error"; message: string } | null>(
    null,
  );
  const [needsCascade, setNeedsCascade] = useState(false);
  const [busy, setBusy] = useState(false);

  const institutionName = (institutionId: number) =>
    catalogs.institutions.find((entry) => entry.id === institutionId)?.name ?? "";

  const choices: Record<EntityKind, Choice[]> = {
    institution: catalogs.institutions.map((item) => ({ id: item.id, label: item.name })),
    "instrument-type": catalogs.instrumentTypes.map((item) => ({
      id: item.id,
      label: item.name,
    })),
    "analysis-type": catalogs.analysisTypes.map((item) => ({
      id: item.id,
      label: item.name,
    })),
    microorganism: catalogs.microorganisms.map((item) => ({
      id: item.id,
      label: item.scientific_name,
    })),
    researcher: catalogs.researchers.map((item) => ({
      id: item.id,
      label: `${item.full_name} — ${institutionName(item.institution_id)}`,
    })),
    instrument: catalogs.institutionInstruments.map((item) => ({
      id: item.id,
      label: `${item.display_name || `Instrument ${item.id}`} — ${institutionName(
        item.institution_id,
      )}`,
    })),
    analysis: catalogs.institutionAnalyses.map((item) => ({
      id: item.id,
      label: `${item.public_name || `Offering ${item.id}`} — ${institutionName(
        item.institution_id,
      )}`,
    })),
  };

  const reset = () => {
    setId("");
    setConfirming(false);
    setNeedsCascade(false);
  };

  const run = async (cascade: boolean) => {
    if (!kind || !id) return;
    setBusy(true);
    setStatus(null);
    try {
      const answer = await api.removeEntity({ kind, id: Number(id) }, cascade);
      setStatus({ kind: "ok", message: answer.detail });
      reset();
      onChanged();
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Could not delete";
      setStatus({ kind: "error", message });
      // A held institution is refused until the caller asks to take its contents.
      setNeedsCascade(reason instanceof ApiError && reason.status === 409 && kind === "institution");
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  };

  const options = kind ? choices[kind] : [];

  return (
    <div className="card-form">
      <h3>Delete a record</h3>
      <p className="form-hint">
        A catalogue entry still in use cannot be deleted; disconnect or delete what
        depends on it first. Deleting a researcher is how someone who has left the
        institution is removed, because their affiliation is part of the record rather
        than a connection.
      </p>
      <div className="form-grid">
        <Select
          label="Kind"
          value={kind}
          onChange={(value) => {
            setKind(value as EntityKind | "");
            reset();
            setStatus(null);
          }}
          placeholder="Select a kind"
        >
          <option value="institution">Institution</option>
          <option value="instrument-type">Instrument type</option>
          <option value="analysis-type">Analysis type</option>
          <option value="microorganism">Target organism</option>
          <option value="researcher">Researcher</option>
          <option value="instrument">Institution instrument</option>
          <option value="analysis">Analysis offering</option>
        </Select>
        <Select
          label="Record"
          value={id}
          onChange={(value) => {
            setId(value);
            setConfirming(false);
            setNeedsCascade(false);
          }}
          placeholder={kind ? "Select a record" : "Choose a kind first"}
        >
          {options.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </Select>
      </div>

      <div className="form-footer">
        {!confirming ? (
          <button
            type="button"
            className="danger"
            disabled={!kind || !id || busy}
            onClick={() => {
              setConfirming(true);
              setStatus(null);
              setNeedsCascade(false);
            }}
          >
            Delete
          </button>
        ) : (
          <>
            <button
              type="button"
              className="danger"
              disabled={busy}
              onClick={() => void run(false)}
            >
              {busy ? "Deleting…" : "Yes, delete it"}
            </button>
            <button type="button" className="secondary" onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </>
        )}

        {needsCascade && (
          <button
            type="button"
            className="danger"
            disabled={busy}
            onClick={() => void run(true)}
          >
            Delete it and everything it holds
          </button>
        )}

        {status && (
          <span className={status.kind === "ok" ? "form-ok" : "form-error"}>
            {status.message}
          </span>
        )}
      </div>
    </div>
  );
}
