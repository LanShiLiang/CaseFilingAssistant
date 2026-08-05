import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EligibilityGate } from "./EligibilityGate";

describe("EligibilityGate", () => {
  it("只有一次总确认后才允许新建事项", async () => {
    const create = vi.fn(async () => undefined);
    render(<EligibilityGate onCreate={create} />);

    const button = screen.getByRole("button", { name: "新建强制执行事项" });
    expect(button).toBeDisabled();
    expect(screen.getAllByRole("listitem")).toHaveLength(4);

    fireEvent.click(screen.getByRole("checkbox"));
    expect(button).toBeEnabled();
    fireEvent.click(button);
    expect(create).toHaveBeenCalledTimes(1);
  });
});
