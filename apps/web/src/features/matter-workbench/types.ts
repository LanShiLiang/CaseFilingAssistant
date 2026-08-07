import type { DocumentKind, Matter } from "@case-filing/contracts";

export type FormState = Record<string, string>;
export type FieldChangeHandler = (name: string, value: string) => void;
export type UploadHandler = (kind: DocumentKind, file: File) => Promise<void>;

export interface StepCommonProps {
  matter: Matter;
  fields: FormState;
  onFieldChange: FieldChangeHandler;
}
