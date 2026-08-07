import type { FieldChangeHandler } from "../types";

export function Field({
  label,
  name,
  value,
  onChange,
  required = false,
  readOnly = false,
  type = "text",
  hint
}: {
  label: string;
  name: string;
  value: string;
  onChange: FieldChangeHandler;
  required?: boolean;
  readOnly?: boolean;
  type?: string;
  hint?: string | undefined;
}) {
  return (
    <label className="form-field">
      <span>{label}{required ? <em>必填</em> : null}</span>
      <input
        name={name}
        value={value}
        type={type}
        readOnly={readOnly}
        onChange={(event) => onChange(name, event.target.value)}
      />
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}
