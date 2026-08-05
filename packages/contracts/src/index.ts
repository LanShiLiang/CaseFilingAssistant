export type DocumentKind =
  | "legal_basis"
  | "applicant_id_front"
  | "applicant_id_back"
  | "respondent_id_front"
  | "respondent_id_back"
  | "performance_evidence";

export type JobStatus =
  | "pending"
  | "running"
  | "retry_scheduled"
  | "completed"
  | "failed_terminal";

export type ConfirmationState = "pending" | "confirmed" | "invalidated";

export interface SourceReference {
  document_id: string;
  page: number | null;
  snippet: string;
  extraction_method: "text" | "ocr" | "user";
  confidence: number | null;
}

export interface MatterDocument {
  id: string;
  kind: DocumentKind;
  filename: string;
  parse_status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
}

export interface Matter {
  id: string;
  workflow_profile: "self_single_v1";
  eligibility_version: string;
  eligibility_confirmed: boolean;
  revision: number;
  title_state: "pending_upload" | "processing" | "pending_confirmation" | "case_number_ready";
  display_title: string;
  facts: Record<string, string>;
  confirmations: Record<string, ConfirmationState>;
  sources: Record<string, SourceReference[]>;
  documents: MatterDocument[];
  validated_revision: number | null;
  generated_revision: number | null;
  latest_generation_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  kind: "parse_document" | "generate_package";
  status: JobStatus;
  attempt: number;
  max_attempts: number;
  progress: number | null;
  error_code: string | null;
  result: Record<string, unknown>;
}

export interface ValidationIssue {
  code: string;
  severity: "blocking" | "warning" | "info";
  field: string | null;
  message: string;
}

export interface ValidationResult {
  matter_id: string;
  revision: number;
  blocking_count: number;
  issues: ValidationIssue[];
}

export interface Generation {
  id: string;
  matter_id: string;
  revision: number;
  status: "pending" | "processing" | "completed" | "superseded" | "failed";
  final_confirmed: boolean;
  preview_url: string | null;
  download_url: string | null;
  sha256: string | null;
  created_at: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: Record<string, unknown>;
  };
}

export type { components, operations, paths } from "./generated";
