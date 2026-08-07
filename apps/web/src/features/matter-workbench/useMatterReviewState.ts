"use client";

import { useState } from "react";

import type { Matter } from "@case-filing/contracts";

export type ReviewMatter = Pick<Matter, "revision" | "confirmations" | "scope_signals">;

interface ReviewDraft {
  revision: number;
  confirmedFields: string[];
  dismissedScopeSignals: string[];
}

function reviewDraftFor(matter: ReviewMatter, current: ReviewDraft | null): ReviewDraft {
  if (current?.revision === matter.revision) return current;
  return {
    revision: matter.revision,
    confirmedFields: Object.entries(matter.confirmations)
      .filter(([, status]) => status === "confirmed")
      .map(([field]) => field),
    dismissedScopeSignals: matter.scope_signals
      .filter((signal) => signal.status === "dismissed_as_parse_error")
      .map((signal) => signal.id)
  };
}

function setMembership(values: readonly string[], value: string, included: boolean): string[] {
  return included
    ? [...new Set([...values, value])]
    : values.filter((item) => item !== value);
}

export function useMatterReviewState(matter: ReviewMatter | undefined) {
  const [draft, setDraft] = useState<ReviewDraft | null>(null);
  const currentDraft = draft?.revision === matter?.revision ? draft : null;

  function isFieldConfirmed(name: string): boolean {
    if (!matter) return false;
    return currentDraft
      ? currentDraft.confirmedFields.includes(name)
      : matter.confirmations[name] === "confirmed";
  }

  function setFieldConfirmed(name: string, confirmed: boolean) {
    if (!matter) return;
    setDraft((current) => {
      const base = reviewDraftFor(matter, current);
      return {
        ...base,
        confirmedFields: setMembership(base.confirmedFields, name, confirmed)
      };
    });
  }

  function setScopeSignalDismissed(id: string, dismissed: boolean) {
    if (!matter) return;
    setDraft((current) => {
      const base = reviewDraftFor(matter, current);
      return {
        ...base,
        dismissedScopeSignals: setMembership(base.dismissedScopeSignals, id, dismissed)
      };
    });
  }

  function invalidateField(name: string) {
    if (!matter) return;
    setDraft((current) => {
      const base = reviewDraftFor(matter, current);
      const invalidated = new Set([name]);
      if (name === "judgment_amount" || name === "paid_amount") {
        invalidated.add("outstanding_amount");
      }
      return {
        ...base,
        confirmedFields: base.confirmedFields.filter((field) => !invalidated.has(field))
      };
    });
  }

  return {
    isFieldConfirmed,
    setFieldConfirmed,
    setScopeSignalDismissed,
    invalidateField,
    dismissedScopeSignalIds: currentDraft?.dismissedScopeSignals ?? [],
    reset: () => setDraft(null)
  };
}
