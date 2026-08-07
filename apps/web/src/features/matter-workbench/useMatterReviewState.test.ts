import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useMatterReviewState, type ReviewMatter } from "./useMatterReviewState";

describe("useMatterReviewState", () => {
  it("编辑金额时撤销字段及其派生金额确认", () => {
    const matter: ReviewMatter = {
      revision: 3,
      confirmations: {
        judgment_amount: "confirmed",
        outstanding_amount: "confirmed"
      },
      scope_signals: []
    };
    const { result } = renderHook(() => useMatterReviewState(matter));

    act(() => result.current.invalidateField("judgment_amount"));

    expect(result.current.isFieldConfirmed("judgment_amount")).toBe(false);
    expect(result.current.isFieldConfirmed("outstanding_amount")).toBe(false);
  });

  it("revision 更新后丢弃旧的本地确认草稿", () => {
    const initialMatter: ReviewMatter = {
      revision: 3,
      confirmations: { case_number: "pending" },
      scope_signals: []
    };
    const { result, rerender } = renderHook(
      ({ matter }: { matter: ReviewMatter }) => useMatterReviewState(matter),
      { initialProps: { matter: initialMatter } }
    );
    act(() => result.current.setFieldConfirmed("case_number", true));
    expect(result.current.isFieldConfirmed("case_number")).toBe(true);

    rerender({
      matter: {
        revision: 4,
        confirmations: { case_number: "pending" },
        scope_signals: []
      }
    });

    expect(result.current.isFieldConfirmed("case_number")).toBe(false);
  });
});
