import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Matter, SourceReference } from "@case-filing/contracts";

import { MatterField, MatterFormProvider } from "./MatterForm";

describe("MatterForm", () => {
  it("从同一上下文绑定未提交字段和来源", () => {
    const source: SourceReference = {
      document_id: "document-1",
      parse_revision: 2,
      page: 1,
      snippet: "（2026）测字第001号",
      extraction_method: "text",
      confidence: 0.99
    };
    render(
      <MatterFormProvider
        matter={{
          sources: { case_number: [source] },
          confirmations: { case_number: "pending" }
        } as unknown as Matter}
        fields={{ case_number: "（2026）测字第001号" }}
        onFieldChange={vi.fn()}
        isFieldEdited={() => false}
      >
        <MatterField label="案号" name="case_number" />
      </MatterFormProvider>
    );

    expect(screen.getByLabelText("案号")).toHaveValue("（2026）测字第001号");
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByText(/材料第 1 页/)).toBeVisible();
  });
});
