import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Matter } from "@case-filing/contracts";

import { MatterFormProvider } from "../MatterForm";
import { ApplicationDetails } from "./ApplicationDetails";

const matter = {
  documents: [],
  sources: {}
} as unknown as Matter;

describe("ApplicationDetails", () => {
  it("以明文输入展示联系、送达、收款和财产线索字段", () => {
    render(
      <MatterFormProvider
        matter={matter}
        fields={{}}
        onFieldChange={vi.fn()}
        isFieldEdited={() => false}
      >
        <ApplicationDetails />
      </MatterFormProvider>
    );

    for (const label of [
      "联系电话",
      "送达地址",
      "收款账户（选填）",
      "已知财产线索（选填）"
    ]) {
      expect(screen.getByLabelText(label, { exact: false })).toHaveAttribute("type", "text");
      expect(screen.queryByRole("button", { name: `显示${label}` })).not.toBeInTheDocument();
    }
    expect(screen.queryByText("申请内容与未履行金额")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("上传履行情况材料")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("文书确定金额（元）")).not.toBeInTheDocument();
  });
});
