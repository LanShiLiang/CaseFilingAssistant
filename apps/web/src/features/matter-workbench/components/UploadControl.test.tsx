import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Matter } from "@case-filing/contracts";

import { UploadControl } from "./UploadControl";

const matter = { documents: [] } as unknown as Matter;

describe("UploadControl", () => {
  it("默认把材料明确标记为必传", () => {
    render(
      <UploadControl
        kind="respondent_id_front"
        label="身份证人像面"
        accept="JPG、PNG"
        matter={matter}
        onUpload={vi.fn()}
      />
    );

    expect(screen.getByLabelText("上传身份证人像面")).toBeRequired();
    expect(screen.getAllByText("必传").length).toBeGreaterThan(0);
  });
});
