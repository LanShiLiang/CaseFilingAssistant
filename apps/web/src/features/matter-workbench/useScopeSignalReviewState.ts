"use client";

import { useState } from "react";

import type { Matter } from "@case-filing/contracts";

export type ScopeReviewMatter = Pick<Matter, "revision" | "scope_signals">;

interface ScopeReviewState {
  revision: number;
  dismissedScopeSignals: string[];
}

function stateFor(
  matter: ScopeReviewMatter,
  current: ScopeReviewState | null
): ScopeReviewState {
  if (current?.revision === matter.revision) return current;
  return {
    revision: matter.revision,
    dismissedScopeSignals: matter.scope_signals
      .filter((signal) => signal.status === "dismissed_as_parse_error")
      .map((signal) => signal.id)
  };
}

export function useScopeSignalReviewState(matter: ScopeReviewMatter | undefined) {
  const [reviewState, setReviewState] = useState<ScopeReviewState | null>(null);
  const currentState = reviewState?.revision === matter?.revision ? reviewState : null;
  const serverDismissedScopeSignals = matter?.scope_signals
    .filter((signal) => signal.status === "dismissed_as_parse_error")
    .map((signal) => signal.id) ?? [];

  function setScopeSignalDismissed(id: string, dismissed: boolean) {
    if (!matter) return;
    setReviewState((current) => {
      const base = stateFor(matter, current);
      return {
        ...base,
        dismissedScopeSignals: dismissed
          ? [...new Set([...base.dismissedScopeSignals, id])]
          : base.dismissedScopeSignals.filter((item) => item !== id)
      };
    });
  }

  return {
    setScopeSignalDismissed,
    dismissedScopeSignalIds:
      currentState?.dismissedScopeSignals ?? serverDismissedScopeSignals,
    reset: () => setReviewState(null)
  };
}
