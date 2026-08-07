import type { DocumentKind } from "@case-filing/contracts";

export type FormState = Record<string, string>;
export type FieldChangeHandler = (name: string, value: string) => void;
export type UploadHandler = (kind: DocumentKind, file: File) => Promise<void>;
export type ExportCheck = "critical" | "review" | "local";
export type ExportCheckValues = Record<ExportCheck, boolean>;
export type ExportCheckState = ExportCheckValues & { generationId: string };
