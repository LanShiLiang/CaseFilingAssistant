---
name: preserve-revisioned-form-input
description: Preserve unsaved user input in CaseFilingAssistant forms when uploads, parsing jobs, polling, RTK Query invalidation, or other background mutations advance the server revision. Use when changing matter-workbench form state, upload flows, revision handling, cache refreshes, save boundaries, or regression tests for cross-section field loss.
---

# Preserve Revisioned Form Input

Protect user-entered values without creating a second server business state machine.

## Establish the state boundary

1. Treat `Matter.facts` and `Matter.revision` as the latest authoritative server baseline.
2. Store only unsaved dirty fields locally, scoped by `matterId`; do not copy a complete server snapshot into local state.
3. Render `latest server fields + dirty field overrides` regardless of revision changes.
4. Drop local edits when switching to a different matter. Never replay one matter's values into another.

## Handle mutations

- Preserve dirty fields after uploads, parsing completion, polling and cache invalidation, even when they advance revision.
- Clear dirty fields only after the matching save mutation succeeds.
- Preserve dirty fields after network errors and `409 revision_conflict` so the user can reconcile and retry.
- Let newly extracted server fields update keys the user has not edited. A dirty user field always wins until save or explicit discard.
- Do not make upload callbacks call a whole-form reset.

## Preserve source and confirmation semantics

- Show a dirty field as `用户填写（保存后记录）`; do not attach a stale material source to a changed local value.
- Treat the step save action as confirmation of the submitted non-empty values when the UI has no per-field confirmation control.
- Keep server confirmations, source references, revision gates and generation eligibility authoritative.
- Never allow a local edit to unlock a server step or generation gate before it is saved.

## Require regression coverage

Add tests that name and protect these invariants:

1. Consecutive edits merge without losing adjacent fields.
2. A server revision refresh updates untouched fields and preserves dirty fields.
3. Pending values never cross `matterId` boundaries.
4. Filling applicant fields and then uploading both respondent identity sides preserves the applicant values after upload and worker completion.
5. A successful save clears pending edits; an error keeps them.

Run the focused frontend tests first, then `pnpm verify` and desktop/mobile `pnpm test:e2e`. Use only synthetic fixtures.

## Review the implementation

Before delivery, search every mutation that can advance revision and verify it does not reset pending edits. Check the rendered source label for edited fields, inspect the actual diff, and confirm the P0 browser sequence with a fresh synthetic matter.
