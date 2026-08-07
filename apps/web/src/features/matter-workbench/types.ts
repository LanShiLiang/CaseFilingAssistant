import type { DocumentKind } from "@case-filing/contracts";

export type FormState = Record<string, string>;
export type FieldChangeHandler = (name: string, value: string) => void;
export type UploadHandler = (kind: DocumentKind, file: File) => Promise<void>;
export type ExportCheck = "critical" | "review" | "local";
export type ExportCheckValues = Record<ExportCheck, boolean>;
export type ExportCheckState = ExportCheckValues & { generationId: string };
export type StepOneBlocker = {
  id: string;
  section: string;
  message: string;
};
export type WorkbenchOperation =
  | { kind: "blocked"; blockers: StepOneBlocker[] }
  | { kind: "save"; phase: "collecting" | "saving" | "validating" }
  | { kind: "preview"; phase: "starting" | "running" };
