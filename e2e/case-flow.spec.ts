import path from "node:path";

import { expect, test } from "@playwright/test";

const fixtureRoot = path.resolve(import.meta.dirname, "..", ".artifacts", "e2e-fixtures");

test("从虚构材料生成并下载可人工复核的强制执行申请材料", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "开始前确认适用条件" })).toBeVisible();

  await page.getByRole("checkbox", { name: "我已阅读并确认以上 4 项全部符合。" }).check();
  await page.getByRole("button", { name: "新建强制执行事项" }).click();
  await expect(page).toHaveURL(/\/matters\/[0-9a-f-]+/);
  await expect(page.getByText("待上传执行依据").first()).toBeVisible();

  await page.getByLabel("上传民事调解书或民事判决书").setInputFiles(
    path.join(fixtureRoot, "synthetic-legal-basis.docx")
  );
  await expect(page.locator('[name="case_number"]')).toHaveValue(
    "（2026）京0105民初123号",
    { timeout: 30_000 }
  );

  const applicant = page.locator("section.panel").filter({
    has: page.getByRole("heading", { name: "申请执行人", exact: true })
  });
  await applicant.getByLabel("上传身份证人像面").setInputFiles(
    path.join(fixtureRoot, "synthetic-id-front.png")
  );
  await expect(applicant).toContainText("synthetic-id-front.png", { timeout: 15_000 });
  const backUpload = applicant.getByLabel("上传身份证国徽面");
  await expect(backUpload).toBeEnabled({ timeout: 15_000 });
  await backUpload.setInputFiles(
    path.join(fixtureRoot, "synthetic-id-back.png")
  );
  await expect(applicant).toContainText("synthetic-id-back.png", { timeout: 15_000 });

  const applicantName = page.locator('[name="applicant_name"]');
  const applicantId = page.locator('[name="applicant_id"]');
  await applicantName.fill("测试申请执行人");
  await applicantId.fill("TEST-ID-APPLICANT");

  const respondent = page.locator("section.panel").filter({
    has: page.getByRole("heading", { name: "被执行人", exact: true })
  });
  await respondent.getByLabel("上传身份证人像面").setInputFiles(
    path.join(fixtureRoot, "synthetic-id-front.png")
  );
  await expect(respondent).toContainText("synthetic-id-front.png", { timeout: 15_000 });
  await expect(applicantName).toHaveValue("测试申请执行人");
  await expect(applicantId).toHaveValue("TEST-ID-APPLICANT");
  await respondent.getByLabel("上传身份证国徽面").setInputFiles(
    path.join(fixtureRoot, "synthetic-id-back.png")
  );
  await expect(respondent).toContainText("synthetic-id-back.png", { timeout: 15_000 });
  await expect(applicantName).toHaveValue("测试申请执行人");
  await expect(applicantId).toHaveValue("TEST-ID-APPLICANT");

  await page.locator('[name="document_date"]').fill("2026-08-06");
  await page.locator('[name="respondent_id"]').fill("TEST-ID-RESPONDENT");
  await page.getByRole("button", { name: "保存并提取申请内容" }).click();
  await expect(page.getByRole("heading", { name: "申请内容" })).toBeVisible();

  await page.locator('[name="paid_amount"]').fill("2500.00");
  await page.locator('[name="request_text"]').fill("请求强制执行人民币7500.00元。");
  await page.locator('[name="filing_court"]').fill("北京市朝阳区人民法院");
  await page.locator('[name="service_address"]').fill("测试地址（非真实）");
  await page.locator('[name="phone"]').fill("TEST-PHONE");
  await page.getByRole("button", { name: "保存并运行检查" }).click();
  await expect(page.getByRole("heading", { name: "检查与预览" })).toBeVisible();

  await page.getByRole("button", { name: "运行当前版本检查" }).click();
  await expect(page.getByText("生成文件必须由用户自行复核", { exact: false })).toBeVisible();
  const generateButton = page.getByRole("button", { name: "生成材料包" });
  await expect(generateButton).toBeEnabled();
  await generateButton.click();
  await expect(page.getByTitle("强制执行申请书预览")).toBeVisible({ timeout: 45_000 });

  await page.getByRole("button", { name: "预览完成，进入导出" }).click();
  await page.getByRole("checkbox", { name: /我已逐项核对姓名/ }).check();
  await page.getByRole("checkbox", { name: /我理解生成文件必须由本人或专业人员复核/ }).check();
  await page.getByRole("checkbox", { name: /我已自行核对受理法院/ }).check();
  await page.getByRole("button", { name: "提交三项声明并解锁下载" }).click();
  const downloadLink = page.getByRole("link", { name: /下载申请强制执行材料包/ });
  await expect(downloadLink).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await downloadLink.click();
  const download = await downloadPromise;
  const saved = path.join(testInfo.outputDir, "application-package.zip");
  await download.saveAs(saved);
  const file = await (await import("node:fs/promises")).stat(saved);
  expect(file.size).toBeGreaterThan(5000);
});
