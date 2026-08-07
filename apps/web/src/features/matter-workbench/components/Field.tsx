"use client";

import { type ChangeEvent, useId, useState } from "react";

import type { ConfirmationState, SourceReference } from "@case-filing/contracts";

import type { FieldChangeHandler, FieldConfirmationHandler } from "../types";

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
  confirmed: boolean;
  onConfirmationChange: FieldConfirmationHandler;
  source?: SourceReference | undefined;
  status?: ConfirmationState | undefined;
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
  confirmed,
  onConfirmationChange,
  source,
  status
}: FieldProps) {
  const id = useId();
  const [revealed, setRevealed] = useState(false);
  const inputType = sensitive && !revealed ? "password" : type;
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
      <label className="field-confirmation">
        <input
          type="checkbox"
          checked={confirmed}
          disabled={!value.trim()}
          onChange={(event) => onConfirmationChange(name, event.target.checked)}
        />
        <span>我已核对当前值与来源</span>
      </label>
      <small>
        状态：{status ?? "pending"}；来源：
        {source
          ? `${source.document_id === "user" ? "用户填写" : `材料第 ${source.page ?? "?"} 页`} · ${source.snippet}`
          : "暂无来源，请人工填写并核对"}
      </small>
      {hint ? <small>{hint}</small> : null}
    </div>
  );
}
