"use client";

import { type ChangeEvent, useId, useState } from "react";

import type { SourceReference } from "@case-filing/contracts";

import type { FieldChangeHandler } from "../types";

export interface FieldProps {
  label: string;
  name: string;
  value: string;
  onChange: FieldChangeHandler;
  required?: boolean;
  readOnly?: boolean;
  type?: string;
  hint?: string | undefined;
  multiline?: boolean;
  sensitive?: boolean;
  edited?: boolean;
  source?: SourceReference | undefined;
}

export function Field({
  label,
  name,
  value,
  onChange,
  required = false,
  readOnly = false,
  type = "text",
  hint,
  multiline = false,
  sensitive = false,
  edited = false,
  source
}: FieldProps) {
  const id = useId();
  const [revealed, setRevealed] = useState(false);
  const inputType = sensitive && !revealed ? "password" : type;
  const sourceDescription = source?.document_id === "user"
    ? "用户填写"
    : source
      ? `材料第 ${source.page ?? "?"} 页 · ${source.snippet}`
      : "";
  const controlProps = {
    id,
    name,
    value,
    readOnly,
    onChange: (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      onChange(name, event.target.value)
  };

  return (
    <div className="form-field">
      <label htmlFor={id}>{label}{required ? <em>必填</em> : null}</label>
      <div className="field-input-row">
        {multiline ? (
          <textarea
            {...controlProps}
            rows={5}
          />
        ) : (
          <input
            {...controlProps}
            type={inputType}
            onBlur={() => setRevealed(false)}
          />
        )}
        {sensitive ? (
          <button
            className="field-reveal"
            type="button"
            aria-label={revealed ? `隐藏${label}` : `显示${label}`}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => setRevealed((current) => !current)}
          >
            {revealed ? "隐藏" : "显示"}
          </button>
        ) : null}
      </div>
      {edited ? <small>来源：用户填写（保存后记录）</small> : null}
      {!edited && source ? (
        <small>来源：{sourceDescription}</small>
      ) : null}
      {hint ? <small>{hint}</small> : null}
    </div>
  );
}
