import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { StepNavigation } from "./StepNavigation";

describe("StepNavigation", () => {
  it("只允许进入服务端开放的步骤", () => {
    const navigate = vi.fn();
    render(
      <StepNavigation
        activeStep={1}
        allowedSteps={[true, false, false, false]}
        onNavigate={navigate}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /当事人与依据/ }));
    expect(navigate).toHaveBeenCalledWith(1);
    expect(screen.getByRole("button", { name: /申请内容/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /导出/ })).toBeDisabled();
  });
});
