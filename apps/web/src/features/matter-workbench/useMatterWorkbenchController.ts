"use client";

import { useEffect, useState } from "react";

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
  const [checkedGenerationId, setCheckedGenerationId] = useState<string | null>(null);

  const [uploadDocument, uploadState] = useUploadDocumentMutation();
  const [saveFacts, saveState] = useSaveFactsMutation();
  const [validateMatter, validateState] = useValidateMatterMutation();
  const [startGeneration, generationStartState] = useStartGenerationMutation();
  const [confirmGeneration, confirmState] = useConfirmGenerationMutation();
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
    effectiveGenerationId && checkedGenerationId === effectiveGenerationId
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
  }

  async function handleUpload(kind: DocumentKind, file: File) {
    if (!matter) return;
    setError("");
    try {
      const result = await uploadDocument({
        matterId,
        kind,
        expectedRevision: matter.revision,
        file
      }).unwrap();
      setJobId(result.job_id);
      setDraft(null);
      setValidation(null);
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
        confirm_fields: names.filter((name) => Boolean(payload[name]?.trim()))
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
        confirm_fields: names.filter((name) => Boolean(payload[name]?.trim()))
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
        expected_revision: matter.revision
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
        expected_revision: matter.revision
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
        expected_revision: matter.revision
      }).unwrap();
      await refetchGeneration();
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
    navigate,
    updateField,
    handleUpload,
    saveStepOne,
    saveStepTwo,
    runValidation,
    generate,
    confirmAndUnlock,
    setFinalChecked: (checked: boolean) =>
      setCheckedGenerationId(checked ? effectiveGenerationId : null)
  };
}
