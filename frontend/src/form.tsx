import { FormEvent, ReactNode, useState } from "react";

export function Select({
  label,
  value,
  onChange,
  children,
  placeholder = "Any",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
  /** Text of the empty option. Pass null for a select that always has a value. */
  placeholder?: string | null;
  required?: boolean;
}) {
  return (
    <label>
      <span>{label}</span>
      <select
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
      >
        {placeholder !== null && <option value="">{placeholder}</option>}
        {children}
      </select>
    </label>
  );
}

export function Input({
  label,
  value,
  onChange,
  required = false,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  type?: string;
  placeholder?: string;
}) {
  return (
    <label>
      <span>{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

/**
 * A create/connect form. `onSubmit` resolves to the confirmation message shown
 * on success; a rejection is rendered as an inline error and nothing is reset.
 */
export function CreateForm({
  title,
  hint,
  submitLabel,
  onSubmit,
  onDone,
  children,
}: {
  title: string;
  hint?: string;
  submitLabel: string;
  onSubmit: () => Promise<string>;
  onDone: () => void;
  children: ReactNode;
}) {
  const [status, setStatus] = useState<{ kind: "ok" | "error"; message: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setStatus(null);
    try {
      const message = await onSubmit();
      setStatus({ kind: "ok", message });
      onDone();
    } catch (reason) {
      setStatus({
        kind: "error",
        message: reason instanceof Error ? reason.message : "Request failed",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card-form" onSubmit={submit}>
      <h3>{title}</h3>
      {hint && <p className="form-hint">{hint}</p>}
      <div className="form-grid">{children}</div>
      <div className="form-footer">
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Saving…" : submitLabel}
        </button>
        {status && (
          <span className={status.kind === "ok" ? "form-ok" : "form-error"}>
            {status.message}
          </span>
        )}
      </div>
    </form>
  );
}
