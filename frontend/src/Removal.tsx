import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import { Select } from "./form";
import { useT, type MessageKey } from "./i18n";
import type { AnalysisDetailView, Catalogs, EntityKind, EntityRef } from "./types";

/**
 * The connections an analysis offering currently states, each removable.
 *
 * Disconnecting leaves both records standing: the instrument is still owned,
 * the researcher still employed. Only the statement that they belong together
 * goes away, and with it the capability's searchability through that link.
 */
export function CurrentConnections({
  analysisId,
  version = 0,
  onChanged,
}: {
  analysisId: number;
  /** Raised by the caller when a connection was added elsewhere on the page. */
  version?: number;
  onChanged: () => void;
}) {
  const t = useT();
  const [detail, setDetail] = useState<AnalysisDetailView | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);

  useEffect(() => {
    let active = true;
    setDetail(null);
    api
      .detail({ kind: "analysis", id: analysisId })
      .then((answer) => {
        if (active && answer.kind === "analysis") setDetail(answer.data);
      })
      .catch(() => {
        if (active) setError(t("current.readFailed"));
      });
    return () => {
      active = false;
    };
  }, [analysisId, version, reloads, t]);

  const disconnect = async (key: string, run: () => Promise<unknown>) => {
    setBusy(key);
    setError("");
    try {
      await run();
      setReloads((current) => current + 1);
      onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("current.disconnectFailed"));
    } finally {
      setBusy(null);
    }
  };

  if (!detail) {
    return (
      <div className="card-form">
        <h3>{t("current.title")}</h3>
        <p className="empty">{error || t("common.loading")}</p>
      </div>
    );
  }

  const rows = [
    ...detail.instruments.map((item) => ({
      key: `instrument-${item.id}`,
      label: item.display_name || item.type_name,
      note: t("current.usesInstrument"),
      run: () => api.unlinkInstrument(detail.id, item.id),
    })),
    ...detail.targets.map((item) => ({
      key: `target-${item.id}`,
      label: item.scientific_name,
      note: t("current.detectsOrganism"),
      run: () => api.unlinkTarget(detail.id, item.id),
    })),
    ...detail.researchers.map((item) => ({
      key: `researcher-${item.id}`,
      label: item.full_name,
      note: item.role
        ? t("current.performedByAs", { role: item.role })
        : t("current.performedBy"),
      run: () => api.unlinkResearcher(detail.id, item.id),
    })),
  ];

  return (
    <div className="card-form">
      <h3>{t("current.title")}</h3>
      <p className="form-hint">{t("current.hint")}</p>
      {error && <p className="form-error">{error}</p>}
      {rows.length === 0 ? (
        <p className="empty">{t("current.empty")}</p>
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
                {busy === row.key ? t("common.removing") : t("current.disconnect")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

type Choice = { id: number; label: string };

/** The kinds that can be deleted, in the order the select offers them. */
const KIND_OPTIONS: [EntityKind, MessageKey][] = [
  ["institution", "kind.institution"],
  ["instrument-type", "kind.instrument-type"],
  ["analysis-type", "kind.analysis-type"],
  ["microorganism", "kind.microorganism"],
  ["researcher", "kind.researcher"],
  ["instrument", "manage.instrument.title"],
  ["analysis", "kind.analysis"],
];

/** Delete a record, after saying what will go with it. */
export function RemoveRecordForm({
  catalogs,
  onChanged,
}: {
  catalogs: Catalogs;
  onChanged: () => void;
}) {
  const t = useT();
  const [kind, setKind] = useState<EntityKind | "">("");
  const [id, setId] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [status, setStatus] = useState<{ kind: "ok" | "error"; message: string } | null>(
    null,
  );
  /**
   * The record a refusal was about, not whatever is selected now.
   *
   * The reply arrives after the request, by which time the selection may have
   * moved on. Offering "delete everything it holds" against the current
   * selection would cascade over a record nobody asked about.
   */
  const [cascade, setCascade] = useState<{ ref: EntityRef; label: string } | null>(null);
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
      label: `${
        item.display_name || t("connect.unnamedInstrument", { id: item.id })
      } — ${institutionName(item.institution_id)}`,
    })),
    analysis: catalogs.institutionAnalyses.map((item) => ({
      id: item.id,
      label: `${
        item.public_name || t("connect.unnamedOffering", { id: item.id })
      } — ${institutionName(item.institution_id)}`,
    })),
  };

  const options = kind ? choices[kind] : [];

  const reset = () => {
    setId("");
    setConfirming(false);
    setCascade(null);
  };

  /** Delete one named record. The target is fixed when the request is made. */
  const run = async (target: EntityRef, label: string, withContents: boolean) => {
    setBusy(true);
    setStatus(null);
    try {
      const answer = await api.removeEntity(target, withContents);
      setStatus({ kind: "ok", message: answer.detail });
      reset();
      onChanged();
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : t("delete.failed");
      setStatus({ kind: "error", message });
      const held =
        reason instanceof ApiError &&
        reason.status === 409 &&
        target.kind === "institution";
      setCascade(held ? { ref: target, label } : null);
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  };

  const selected = options.find((item) => String(item.id) === id);
  const target: EntityRef | null = kind && id ? { kind, id: Number(id) } : null;


  return (
    <div className="card-form">
      <h3>{t("delete.title")}</h3>
      <p className="form-hint">{t("delete.hint")}</p>
      <div className="form-grid">
        <Select
          label={t("manage.field.kind")}
          value={kind}
          disabled={busy}
          onChange={(value) => {
            setKind(value as EntityKind | "");
            reset();
            setStatus(null);
          }}
          placeholder={t("manage.pick.kind")}
        >
          {KIND_OPTIONS.map(([value, key]) => (
            <option key={value} value={value}>
              {t(key)}
            </option>
          ))}
        </Select>
        <Select
          label={t("manage.field.record")}
          value={id}
          disabled={busy}
          onChange={(value) => {
            setId(value);
            setConfirming(false);
            setCascade(null);
          }}
          placeholder={kind ? t("manage.pick.record") : t("manage.pick.kindFirst")}
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
            disabled={!target || busy}
            onClick={() => {
              setConfirming(true);
              setStatus(null);
              setCascade(null);
            }}
          >
            {t("common.delete")}
          </button>
        ) : (
          <>
            <button
              type="button"
              className="danger"
              disabled={busy || !target}
              onClick={() => {
                if (target) void run(target, selected?.label ?? "", false);
              }}
            >
              {busy
                ? t("common.deleting")
                : t("delete.confirm", {
                    label: selected?.label ?? t("delete.confirmIt"),
                  })}
            </button>
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => setConfirming(false)}
            >
              {t("common.cancel")}
            </button>
          </>
        )}

        {cascade && (
          <button
            type="button"
            className="danger"
            disabled={busy}
            onClick={() => void run(cascade.ref, cascade.label, true)}
          >
            {t("delete.cascade", { label: cascade.label })}
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
