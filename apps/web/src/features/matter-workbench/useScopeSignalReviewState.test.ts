import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  useScopeSignalReviewState,
  type ScopeReviewMatter
} from "./useScopeSignalReviewState";

describe("useScopeSignalReviewState", () => {
  it("只维护复杂性信号的人工排除选择", () => {
    const matter: ScopeReviewMatter = {
      revision: 3,
      scope_signals: [
        {
          id: "signal-1",
          code: "unsupported_multiple_respondents",
          document_id: "document-1",
          page: 1,
          snippet: "测试信号",
          status: "open"
        }
      ]
    };
    const { result } = renderHook(() => useScopeSignalReviewState(matter));

    act(() => result.current.setScopeSignalDismissed("signal-1", true));
    expect(result.current.dismissedScopeSignalIds).toEqual(["signal-1"]);

    act(() => result.current.setScopeSignalDismissed("signal-1", false));
    expect(result.current.dismissedScopeSignalIds).toEqual([]);
  });

  it("revision 更新后重新使用服务端复杂性信号状态", () => {
    const initialMatter: ScopeReviewMatter = { revision: 3, scope_signals: [] };
    const { result, rerender } = renderHook(
      ({ matter }: { matter: ScopeReviewMatter }) => useScopeSignalReviewState(matter),
      { initialProps: { matter: initialMatter } }
    );

    rerender({
      matter: {
        revision: 4,
        scope_signals: [
          {
            id: "signal-2",
            code: "unsupported_multiple_applicants",
            document_id: "document-2",
            page: 2,
            snippet: "测试信号",
            status: "dismissed_as_parse_error"
          }
        ]
      }
    });

    expect(result.current.dismissedScopeSignalIds).toEqual(["signal-2"]);
  });
});
