import { CheckCircle2, Upload } from "lucide-react";

import type { DocumentKind, Matter } from "@case-filing/contracts";

import type { UploadHandler } from "../types";

export function UploadControl({
  kind,
  label,
  accept,
  matter,
  onUpload,
  optional = false,
  disabled = false
}: {
  kind: DocumentKind;
  label: string;
  accept: string;
  matter: Matter;
  onUpload: UploadHandler;
  optional?: boolean;
  disabled?: boolean;
}) {
  const document = matter.documents.find((item) => item.kind === kind && item.active);
  return (
    <label className={`upload-control ${document ? "upload-control--done" : ""}`}>
      <input
        aria-label={`上传${label}`}
        type="file"
        accept={accept.includes("PDF") ? ".pdf,.docx,.jpg,.jpeg,.png" : ".jpg,.jpeg,.png"}
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void onUpload(kind, file);
          event.target.value = "";
        }}
      />
      {document ? <CheckCircle2 size={22} /> : <Upload size={22} />}
      <span><strong>{label}</strong><small>{document ? `${document.filename} · ${document.parse_status}` : `${accept}${optional ? " · 选填" : ""}`}</small></span>
    </label>
  );
}
