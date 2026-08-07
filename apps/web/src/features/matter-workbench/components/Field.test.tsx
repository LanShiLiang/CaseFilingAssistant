import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Field } from "./Field";

describe("Field", () => {
  it("遮罩敏感值并只展示来源，不渲染逐字段确认或内部状态", () => {
    const onChange = vi.fn();
    render(
      <Field
        label="身份证号"
        name="applicant_id"
        value="TEST-ID-APPLICANT"
        onChange={onChange}
        sensitive
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

    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByText("来源：用户填写")).toBeVisible();
    expect(screen.queryByText(/状态：/)).not.toBeInTheDocument();
  });

  it("用户编辑值时展示待保存的用户填写来源", () => {
    render(
      <Field
        label="联系电话"
        name="phone"
        value="TEST-PHONE"
        onChange={vi.fn()}
        edited
      />
    );

    expect(screen.getByText("来源：用户填写（保存后记录）")).toBeVisible();
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
      />
    );

    const textarea = screen.getByLabelText("请求事项");
    expect(textarea.tagName).toBe("TEXTAREA");
    expect(textarea).toHaveAttribute("name", "request_text");
    expect(textarea).toHaveValue("请求被执行人履行义务");
    expect(textarea).toHaveAttribute("readonly");
  });
});
