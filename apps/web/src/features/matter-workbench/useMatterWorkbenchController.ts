"use client";

import { useEffect, useRef, useState } from "react";

import type { DocumentKind, ValidationResult } from "@case-filing/contracts";

import {
  applyPendingEdits,
  mergePendingField,
  parseApiError
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

import type { ExportCheck, ExportCheckState, WorkbenchOperation } from "./types";
import {
  blockingIssuesToStepOneBlockers,
  collectStepOneBlockers,
  STEP_ONE_SUBMISSION_FIELDS
} from "./stepOneRequirements";
import { useScopeSignalReviewState } from "./useScopeSignalReviewState";
import { WORKFLOW_STEPS } from "./workflow";

function suggestedStep(allowed: readonly boolean[]): number {
  let result = 1;
  allowed.forEach((item, index) => {
    if (item) result = index + 1;
  });
  return result;
}

export function useMatterWorkbenchController(matterId: string) {
  const { data: matter, isLoading, error: queryError, refetch } = useGetMatterQuery(matterId);
  const scopeReview = useScopeSignalReviewState(matter);
  const [requestedStep, setRequestedStep] = useState<number | null>(null);
  const [pendingEdits, setPendingEdits] = useState<ReturnType<typeof mergePendingField> | null>(null);
  const [error, setError] = useState("");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [operation, setOperation] = useState<WorkbenchOperation | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [exportChecks, setExportChecks] = useState<ExportCheckState>({
    generationId: "",
    critical: false,
    review: false,
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
        const timer = window.setTimeout(() => {
          setJobId(null);
          setOperation((current) => current?.kind === "preview" ? null : current);
        }, 0);
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
    exportChecks.review &&
    exportChecks.local
  );

  const gates = WORKFLOW_STEPS.map(({ gateKey }) =>
    matter?.step_gates.find((gate) => gate.step === gateKey)
  );
  const allowedSteps = gates.map((gate, index) => index === 0 || Boolean(gate?.allowed));
  const fallbackStep = suggestedStep(allowedSteps);
  const activeStep = requestedStep && allowedSteps[requestedStep - 1]
    ? requestedStep
    : fallbackStep;

  const fields = matter
    ? applyPendingEdits(matter.facts, pendingEdits, matter.id)
    : {};
  function navigate(step: number) {
    if (allowedSteps[step - 1]) setRequestedStep(step);
  }

  function updateField(name: string, value: string) {
    if (!matter) return;
    setPendingEdits((current) => mergePendingField(current, matter.id, name, value));
  }

  function idempotencyKey(scope: string, payload: unknown): string {
    const signature = `${scope}:${JSON.stringify(payload)}`;
    const existing = idempotencyKeys.current.get(signature);
    if (existing) return existing;
    const created = crypto.randomUUID();
    idempotencyKeys.current.set(signature, created);
    return created;
  }

  async function runMutation<T>(
    request: () => Promise<T>,
    onSuccess?: (result: T) => void | Promise<void>
  ): Promise<void> {
    setError("");
    try {
      const result = await request();
      await onSuccess?.(result);
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function handleUpload(kind: DocumentKind, file: File) {
    if (!matter) return;
    await runMutation(
      () =>
        uploadDocument({
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
        }).unwrap(),
      async (result) => {
        setJobId(result.job_id);
        setValidation(null);
        scopeReview.reset();
        await refetch();
      }
    );
  }

  async function saveStepOne() {
    if (!matter || operation) return;
    const blockers = collectStepOneBlockers(matter, fields);
    if (blockers.length) {
      setError("");
      setOperation({ kind: "blocked", blockers });
      return;
    }

    setError("");
    setOperation({ kind: "save", phase: "collecting" });
    await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()));

    const values: Record<string, string> = {
      ...fields,
      paid_amount: fields.paid_amount?.trim() || "0.00"
    };
    const names = [...new Set(STEP_ONE_SUBMISSION_FIELDS)];
    const payload = Object.fromEntries(names.map((name) => [name, values[name] ?? ""]));
    const confirmedFields = names.filter((name) => Boolean(payload[name]?.trim()));
    const dismissedScopeSignalIds = scopeReview.dismissedScopeSignalIds;

    setOperation({ kind: "save", phase: "saving" });
    try {
      const savedMatter = await saveFacts({
        matterId,
        expected_revision: matter.revision,
        fields: payload,
        confirm_fields: confirmedFields,
        dismissed_scope_signal_ids: [...dismissedScopeSignalIds],
        idempotencyKey: idempotencyKey("save-details", {
          matterId,
          revision: matter.revision,
          payload,
          confirmed: confirmedFields,
          dismissed: dismissedScopeSignalIds
        })
      }).unwrap();

      // 保存成功才清空 dirty 字段；检查必须使用保存响应返回的新 revision。
      setPendingEdits(null);
      setValidation(null);
      setOperation({ kind: "save", phase: "validating" });
      const result = await validateMatter({
        matterId,
        expected_revision: savedMatter.revision,
        idempotencyKey: idempotencyKey("validate-after-save", {
          matterId,
          revision: savedMatter.revision
        })
      }).unwrap();
      setValidation(result);
      await refetch();
      const validationBlockers = blockingIssuesToStepOneBlockers(result.issues);
      if (validationBlockers.length) {
        setOperation({ kind: "blocked", blockers: validationBlockers });
        return;
      }
      setRequestedStep(2);
      setOperation(null);
    } catch (reason) {
      setError(parseApiError(reason));
      await refetch();
      setOperation(null);
    }
  }

  function dismissOperation() {
    setOperation((current) => current?.kind === "blocked" ? null : current);
  }

  async function runValidation() {
    if (!matter) return;
    await runMutation(
      () =>
        validateMatter({
          matterId,
          expected_revision: matter.revision,
          idempotencyKey: idempotencyKey("validate", {
            matterId,
            revision: matter.revision
          })
        }).unwrap(),
      async (result) => {
        setValidation(result);
        await refetch();
      }
    );
  }

  async function generate() {
    if (!matter || operation) return;
    setError("");
    setOperation({ kind: "preview", phase: "starting" });
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
      setOperation({ kind: "preview", phase: "running" });
      await refetch();
    } catch (reason) {
      setError(parseApiError(reason));
      setOperation(null);
    }
  }

  async function confirmAndUnlock() {
    if (!matter || !effectiveGenerationId) return;
    await runMutation(
      () =>
        confirmGeneration({
          generationId: effectiveGenerationId,
          expected_revision: matter.revision,
          critical_fields_reviewed: true,
          manual_review_understood: true,
          local_requirements_reviewed: true,
          idempotencyKey: idempotencyKey("export-attestation", {
            generationId: effectiveGenerationId,
            revision: matter.revision
          })
        }).unwrap(),
      async () => {
        await refetchGeneration();
      }
    );
  }

  async function retryFailedJob() {
    if (!matter || !job?.retryable) return;
    await runMutation(() =>
      retryJob({
        jobId: job.id,
        expected_revision: matter.revision,
        idempotencyKey: idempotencyKey("retry-job", {
          jobId: job.id,
          revision: matter.revision,
          attempt: job.attempt
        })
      }).unwrap()
    );
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
    error,
    validation,
    operation,
    job,
    generation,
    finalChecked,
    anyBusy,
    generationBusy,
    validationPending: validateState.isLoading,
    generationPending: generationStartState.isLoading,
    confirmPending: confirmState.isLoading,
    retryPending: retryState.isLoading,
    isFieldEdited: (name: string) => Boolean(
      pendingEdits && matter &&
      pendingEdits.matterId === matter.id &&
      pendingEdits.editedFields.includes(name)
    ),
    dismissedScopeSignalIds: scopeReview.dismissedScopeSignalIds,
    navigate,
    updateField,
    setScopeSignalDismissed: scopeReview.setScopeSignalDismissed,
    handleUpload,
    saveStepOne,
    dismissOperation,
    runValidation,
    generate,
    confirmAndUnlock,
    retryFailedJob,
    exportChecks,
    setExportCheck: (name: ExportCheck, checked: boolean) =>
      setExportChecks((current) => ({
        ...(current.generationId === effectiveGenerationId
          ? current
          : { generationId: effectiveGenerationId ?? "", critical: false, review: false, local: false }),
        [name]: checked
      }))
  };
}
