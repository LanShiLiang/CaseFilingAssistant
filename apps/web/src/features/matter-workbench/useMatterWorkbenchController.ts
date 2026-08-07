"use client";

import { useEffect, useRef, useState } from "react";

import type { DocumentKind, ValidationResult } from "@case-filing/contracts";

import {
  calculateOutstanding,
  mergeDraftField,
  parseApiError,
  STEP_ONE_FIELDS,
  STEP_TWO_FIELDS
} from "@/lib/domain";
import {
  useConfirmGenerationMutation,
  useGetGenerationQuery,
  useGetJobQuery,
  useGetMatterQuery,
  useRetryJobMutation,
  useSaveFactsMutation,
  useStartGenerationMutation,
  useUploadDocumentMutation,
  useValidateMatterMutation
} from "@/store/caseApi";

import type { FormState } from "./types";

const STEP_KEYS = ["parties_and_basis", "application", "review", "export"] as const;

function suggestedStep(allowed: readonly boolean[]): number {
  let result = 1;
  allowed.forEach((item, index) => {
    if (item) result = index + 1;
  });
  return result;
}

export function useMatterWorkbenchController(matterId: string) {
  const { data: matter, isLoading, error: queryError, refetch } = useGetMatterQuery(matterId);
  const [requestedStep, setRequestedStep] = useState<number | null>(null);
  const [draft, setDraft] = useState<{ revision: number; fields: FormState } | null>(null);
  const [error, setError] = useState("");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [reviewDraft, setReviewDraft] = useState<{
    revision: number;
    confirmedFields: string[];
    dismissedScopeSignals: string[];
  } | null>(null);
  const [exportChecks, setExportChecks] = useState({
    generationId: "",
    critical: false,
    draft: false,
    local: false
  });
  const idempotencyKeys = useRef(new Map<string, string>());

  const [uploadDocument, uploadState] = useUploadDocumentMutation();
  const [saveFacts, saveState] = useSaveFactsMutation();
  const [validateMatter, validateState] = useValidateMatterMutation();
  const [startGeneration, generationStartState] = useStartGenerationMutation();
  const [confirmGeneration, confirmState] = useConfirmGenerationMutation();
  const [retryJob, retryState] = useRetryJobMutation();
  const { data: job } = useGetJobQuery(jobId ?? "", {
    skip: !jobId,
    pollingInterval: jobId ? 800 : 0,
    skipPollingIfUnfocused: true
  });
  const effectiveGenerationId = generationId ?? matter?.latest_generation_id ?? null;
  const { data: generation, refetch: refetchGeneration } = useGetGenerationQuery(
    effectiveGenerationId ?? "",
    {
      skip: !effectiveGenerationId,
      pollingInterval: jobId ? 800 : 0,
      skipPollingIfUnfocused: true
    }
  );

  useEffect(() => {
    if (job?.status === "completed" || job?.status === "failed_terminal") {
      void refetch();
      if (effectiveGenerationId) void refetchGeneration();
      const generationTerminal =
        !effectiveGenerationId ||
        Boolean(
          generation && ["completed", "failed", "superseded"].includes(generation.status)
        );
      if (generationTerminal) {
        const timer = window.setTimeout(() => setJobId(null), 0);
        return () => window.clearTimeout(timer);
      }
    }
    return undefined;
  }, [
    job?.status,
    generation,
    effectiveGenerationId,
    refetch,
    refetchGeneration
  ]);

  const finalChecked = Boolean(
    effectiveGenerationId &&
    exportChecks.generationId === effectiveGenerationId &&
    exportChecks.critical &&
    exportChecks.draft &&
    exportChecks.local
  );

  const gates = STEP_KEYS.map((key) =>
    matter?.step_gates.find((gate) => gate.step === key)
  );
  const allowedSteps = gates.map((gate, index) => index === 0 || Boolean(gate?.allowed));
  const fallbackStep = suggestedStep(allowedSteps);
  const activeStep = requestedStep && allowedSteps[requestedStep - 1]
    ? requestedStep
    : fallbackStep;

  const fields = draft && matter && draft.revision === matter.revision
    ? draft.fields
    : matter?.facts ?? {};
  const outstanding = calculateOutstanding(
    fields.judgment_amount ?? "",
    fields.paid_amount ?? ""
  );

  function navigate(step: number) {
    if (allowedSteps[step - 1]) setRequestedStep(step);
  }

  function updateField(name: string, value: string) {
    if (!matter) return;
    setDraft((current) => mergeDraftField(current, matter.revision, matter.facts, name, value));
    setReviewDraft((current) => {
      const confirmedFields = current?.revision === matter.revision
        ? current.confirmedFields
        : Object.entries(matter.confirmations)
            .filter(([, status]) => status === "confirmed")
            .map(([field]) => field);
      const invalidated = new Set([name]);
      if (name === "judgment_amount" || name === "paid_amount") {
        invalidated.add("outstanding_amount");
      }
      return {
        revision: matter.revision,
        confirmedFields: confirmedFields.filter((field) => !invalidated.has(field)),
        dismissedScopeSignals:
          current?.revision === matter.revision
            ? current.dismissedScopeSignals
            : matter.scope_signals
                .filter((signal) => signal.status === "dismissed_as_parse_error")
                .map((signal) => signal.id)
      };
    });
  }

  function idempotencyKey(scope: string, payload: unknown): string {
    const signature = `${scope}:${JSON.stringify(payload)}`;
    const existing = idempotencyKeys.current.get(signature);
    if (existing) return existing;
    const created = crypto.randomUUID();
    idempotencyKeys.current.set(signature, created);
    return created;
  }

  function isFieldConfirmed(name: string): boolean {
    if (!matter) return false;
    if (reviewDraft?.revision === matter.revision) {
      return reviewDraft.confirmedFields.includes(name);
    }
    return matter.confirmations[name] === "confirmed";
  }

  function setFieldConfirmed(name: string, confirmed: boolean) {
    if (!matter) return;
    setReviewDraft((current) => {
      const base = current?.revision === matter.revision
        ? current.confirmedFields
        : Object.entries(matter.confirmations)
            .filter(([, status]) => status === "confirmed")
            .map(([field]) => field);
      return {
        revision: matter.revision,
        confirmedFields: confirmed
          ? [...new Set([...base, name])]
          : base.filter((field) => field !== name),
        dismissedScopeSignals:
          current?.revision === matter.revision
            ? current.dismissedScopeSignals
            : matter.scope_signals
                .filter((signal) => signal.status === "dismissed_as_parse_error")
                .map((signal) => signal.id)
      };
    });
  }

  function setScopeSignalDismissed(id: string, dismissed: boolean) {
    if (!matter) return;
    setReviewDraft((current) => {
      const base = current?.revision === matter.revision
        ? current.dismissedScopeSignals
        : matter.scope_signals
            .filter((signal) => signal.status === "dismissed_as_parse_error")
            .map((signal) => signal.id);
      return {
        revision: matter.revision,
        confirmedFields:
          current?.revision === matter.revision
            ? current.confirmedFields
            : Object.entries(matter.confirmations)
                .filter(([, status]) => status === "confirmed")
                .map(([field]) => field),
        dismissedScopeSignals: dismissed
          ? [...new Set([...base, id])]
          : base.filter((signalId) => signalId !== id)
      };
    });
  }

  async function handleUpload(kind: DocumentKind, file: File) {
    if (!matter) return;
    setError("");
    try {
      const result = await uploadDocument({
        matterId,
        kind,
        expectedRevision: matter.revision,
        file,
        idempotencyKey: idempotencyKey("upload", {
          matterId,
          kind,
          revision: matter.revision,
          name: file.name,
          size: file.size,
          modified: file.lastModified
        })
      }).unwrap();
      setJobId(result.job_id);
      setDraft(null);
      setValidation(null);
      setReviewDraft(null);
      await refetch();
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function saveStepOne() {
    if (!matter) return;
    setError("");
    const names = [...STEP_ONE_FIELDS, "document_date", "applicant_identity_address", "respondent_id"];
    const payload = Object.fromEntries(
      names
        .filter((name) => fields[name] !== undefined)
        .map((name) => [name, fields[name] ?? ""])
    );
    try {
      await saveFacts({
        matterId,
        expected_revision: matter.revision,
        fields: payload,
        confirm_fields: names.filter(
          (name) => Boolean(payload[name]?.trim()) && isFieldConfirmed(name)
        ),
        dismissed_scope_signal_ids:
          reviewDraft?.revision === matter.revision
            ? reviewDraft.dismissedScopeSignals
            : [],
        idempotencyKey: idempotencyKey("save-step-one", {
          matterId,
          revision: matter.revision,
          payload,
          confirmed: names.filter(isFieldConfirmed),
          dismissed: reviewDraft?.dismissedScopeSignals ?? []
        })
      }).unwrap();
      setDraft(null);
      setRequestedStep(2);
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function saveStepTwo() {
    if (!matter) return;
    setError("");
    const nextFields: FormState = { ...fields, outstanding_amount: outstanding };
    const names = [...STEP_TWO_FIELDS, "phone", "bank_account", "property_clues"];
    const payload = Object.fromEntries(names.map((name) => [name, nextFields[name] ?? ""]));
    try {
      await saveFacts({
        matterId,
        expected_revision: matter.revision,
        fields: payload,
        confirm_fields: names.filter(
          (name) => Boolean(payload[name]?.trim()) && isFieldConfirmed(name)
        ),
        dismissed_scope_signal_ids: [],
        idempotencyKey: idempotencyKey("save-step-two", {
          matterId,
          revision: matter.revision,
          payload,
          confirmed: names.filter(isFieldConfirmed)
        })
      }).unwrap();
      setDraft(null);
      setValidation(null);
      setRequestedStep(3);
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function runValidation() {
    if (!matter) return;
    setError("");
    try {
      const result = await validateMatter({
        matterId,
        expected_revision: matter.revision,
        idempotencyKey: idempotencyKey("validate", {
          matterId,
          revision: matter.revision
        })
      }).unwrap();
      setValidation(result);
      await refetch();
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function generate() {
    if (!matter) return;
    setError("");
    try {
      const result = await startGeneration({
        matterId,
        expected_revision: matter.revision,
        idempotencyKey: idempotencyKey("generate", {
          matterId,
          revision: matter.revision
        })
      }).unwrap();
      setGenerationId(result.generation.id);
      setJobId(result.job_id);
      await refetch();
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function confirmAndUnlock() {
    if (!matter || !effectiveGenerationId) return;
    setError("");
    try {
      await confirmGeneration({
        generationId: effectiveGenerationId,
        expected_revision: matter.revision,
        critical_fields_reviewed: true,
        draft_boundary_understood: true,
        local_requirements_reviewed: true,
        idempotencyKey: idempotencyKey("export-attestation", {
          generationId: effectiveGenerationId,
          revision: matter.revision
        })
      }).unwrap();
      await refetchGeneration();
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function retryFailedJob() {
    if (!matter || !job?.retryable) return;
    setError("");
    try {
      await retryJob({
        jobId: job.id,
        expected_revision: matter.revision,
        idempotencyKey: idempotencyKey("retry-job", {
          jobId: job.id,
          revision: matter.revision,
          attempt: job.attempt
        })
      }).unwrap();
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  const anyBusy = uploadState.isLoading || saveState.isLoading;
  const generationBusy = Boolean(job && ["pending", "running", "retry_scheduled"].includes(job.status));

  return {
    matter,
    isLoading,
    queryError,
    activeStep,
    allowedSteps,
    fields,
    outstanding,
    error,
    validation,
    job,
    generation,
    finalChecked,
    anyBusy,
    generationBusy,
    validationPending: validateState.isLoading,
    generationPending: generationStartState.isLoading,
    confirmPending: confirmState.isLoading,
    retryPending: retryState.isLoading,
    isFieldConfirmed,
    dismissedScopeSignalIds:
      reviewDraft && reviewDraft.revision === matter?.revision
        ? reviewDraft.dismissedScopeSignals
        : [],
    navigate,
    updateField,
    setFieldConfirmed,
    setScopeSignalDismissed,
    handleUpload,
    saveStepOne,
    saveStepTwo,
    runValidation,
    generate,
    confirmAndUnlock,
    retryFailedJob,
    exportChecks,
    setExportCheck: (name: "critical" | "draft" | "local", checked: boolean) =>
      setExportChecks((current) => ({
        ...(current.generationId === effectiveGenerationId
          ? current
          : { generationId: effectiveGenerationId ?? "", critical: false, draft: false, local: false }),
        [name]: checked
      }))
  };
}
