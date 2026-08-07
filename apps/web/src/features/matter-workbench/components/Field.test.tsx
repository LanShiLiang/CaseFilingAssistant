import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Field } from "./Field";

describe("Field", () => {
  it("masks sensitive values and requires an explicit source confirmation", () => {
    const onChange = vi.fn();
    const onConfirmationChange = vi.fn();
    render(
      <Field
        label="身份证号"
        name="applicant_id"
        value="TEST-ID-APPLICANT"
        onChange={onChange}
        sensitive
        confirmed={false}
        onConfirmationChange={onConfirmationChange}
        status="pending"
        source={{
          document_id: "user",
          parse_revision: null,
          page: null,
          snippet: "用户填写",
          extraction_method: "user",
          confidence: null
        }}
      />
    );

    const input = screen.getByLabelText("身份证号");
    expect(input).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByRole("button", { name: "显示身份证号" }));
    expect(input).toHaveAttribute("type", "text");
    fireEvent.blur(input);
    expect(input).toHaveAttribute("type", "password");

    fireEvent.click(screen.getByRole("checkbox", { name: "我已核对当前值与来源" }));
    expect(onConfirmationChange).toHaveBeenCalledWith("applicant_id", true);
    expect(screen.getByText(/状态：pending；来源：用户填写/)).toBeVisible();
  });

  it("does not allow confirming an empty field", () => {
    render(
      <Field
        label="联系电话"
        name="phone"
        value=""
        onChange={vi.fn()}
        confirmed={false}
        onConfirmationChange={vi.fn()}
      />
    );

    expect(screen.getByRole("checkbox", { name: "我已核对当前值与来源" })).toBeDisabled();
  });

  it("shares the field identity and value binding with multiline controls", () => {
    const onChange = vi.fn();
    render(
      <Field
        label="请求事项"
        name="request_text"
        value="请求被执行人履行义务"
        onChange={onChange}
        multiline
        readOnly
        confirmed
        onConfirmationChange={vi.fn()}
      />
    );

    const textarea = screen.getByLabelText("请求事项");
    expect(textarea.tagName).toBe("TEXTAREA");
    expect(textarea).toHaveAttribute("name", "request_text");
    expect(textarea).toHaveValue("请求被执行人履行义务");
    expect(textarea).toHaveAttribute("readonly");
  });
});
