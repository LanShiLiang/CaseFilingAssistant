import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StepHeading } from "./StepHeading";

describe("StepHeading", () => {
  it("用统一结构展示步骤、标题和说明", () => {
    render(
      <StepHeading
        step={3}
        title="检查与预览"
        description="所有阻断项必须修复。"
        icon={<span aria-hidden="true">icon</span>}
      />
    );

    expect(screen.getByText("步骤 3")).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "检查与预览" })).toBeVisible();
    expect(screen.getByText("所有阻断项必须修复。")).toBeVisible();
  });
});
