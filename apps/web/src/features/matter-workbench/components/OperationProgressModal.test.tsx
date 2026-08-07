import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OperationProgressModal } from "./OperationProgressModal";

describe("OperationProgressModal", () => {
  it("保存期间展示阶段进度并明确表单锁定", () => {
    render(
      <OperationProgressModal
        operation={{ kind: "save", phase: "validating" }}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByRole("dialog", { name: "正在检查当前数据" })).toHaveFocus();
    expect(screen.getByRole("progressbar", { name: "处理进度 85%" })).toHaveValue(85);
    expect(screen.getByText(/处理完成前表单已锁定/)).toBeVisible();
  });

  it("预览生成期间展示后台任务的真实进度", () => {
    render(
      <OperationProgressModal
        operation={{ kind: "preview", phase: "running" }}
        jobProgress={64}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByRole("dialog", { name: "正在生成申请书预览" })).toBeVisible();
    expect(screen.getByRole("progressbar", { name: "处理进度 64%" })).toHaveValue(64);
  });

  it("阻断时按模块展示缺失项并允许返回补充", () => {
    const onDismiss = vi.fn();
    render(
      <OperationProgressModal
        operation={{
          kind: "blocked",
          blockers: [
            { id: "document:legal_basis", section: "执行依据", message: "请上传民事调解书或民事判决书。" },
            { id: "field:service_address", section: "请求与联系信息", message: "请填写送达地址。" }
          ]
        }}
        onDismiss={onDismiss}
      />
    );

    expect(screen.getByRole("dialog", { name: "步骤一还有必填项未完成" })).toHaveFocus();
    expect(screen.getByText("请上传民事调解书或民事判决书。")).toBeVisible();
    expect(screen.getByText("请填写送达地址。")).toBeVisible();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "返回补充资料" }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("收集步骤一资料时展示阶段进度", () => {
    render(
      <OperationProgressModal
        operation={{ kind: "save", phase: "collecting" }}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByRole("progressbar", { name: "处理进度 20%" })).toHaveValue(20);
  });
});
