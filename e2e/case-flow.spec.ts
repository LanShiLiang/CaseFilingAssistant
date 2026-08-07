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

  await page.getByRole("button", { name: "保存并进入检查与预览" }).click();
  const blockerDialog = page.getByRole("dialog", { name: "步骤一还有必填项未完成" });
  await expect(blockerDialog).toBeVisible();
  await expect(blockerDialog).toContainText("请上传民事调解书或民事判决书。");
  await expect(blockerDialog).toContainText("申请执行人");
  await expect(blockerDialog).toContainText("被执行人");
  await blockerDialog.getByRole("button", { name: "返回补充资料" }).click();
  await expect(blockerDialog).toBeHidden();

  await page.getByLabel("上传民事调解书或民事判决书").setInputFiles(
    path.join(fixtureRoot, "synthetic-legal-basis.pdf")
  );
  await expect(page.locator('[name="case_number"]')).toHaveValue(
    "（2026）京0105民初123号",
    { timeout: 30_000 }
  );

  const applicant = page.locator("section.panel").filter({
    has: page.getByRole("heading", { name: "申请执行人", exact: true })
  });
  await expect(page.getByLabel("上传民事调解书或民事判决书")).toHaveAttribute("required", "");
  await expect(applicant.getByLabel("上传身份证人像面")).toHaveAttribute("required", "");
  const applicantName = page.locator('[name="applicant_name"]');
  const applicantId = page.locator('[name="applicant_id"]');
  const respondentName = page.locator('[name="respondent_name"]');
  const respondentId = page.locator('[name="respondent_id"]');
  await expect(applicantName).toHaveValue("测试原告甲");
  await expect(applicantId).toHaveValue("999999199001010016");
  await expect(respondentName).toHaveValue("测试被告乙");
  await expect(respondentId).toHaveValue("999999199202020026");

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

  await applicantName.fill("测试申请执行人");
  await applicantId.fill("TEST-ID-APPLICANT");

  const respondent = page.locator("section.panel").filter({
    has: page.getByRole("heading", { name: "被执行人", exact: true })
  });
  await expect(respondent.getByLabel("上传身份证人像面")).toHaveAttribute("required", "");
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
  await respondentId.fill("TEST-ID-RESPONDENT");
  await page.locator('[name="request_text"]').fill("请求强制执行人民币10000.00元。");
  await page.locator('[name="filing_court"]').fill("北京市朝阳区人民法院");
  await page.locator('[name="service_address"]').fill("测试地址（非真实）");
  await page.locator('[name="phone"]').fill("TEST-PHONE");

  for (const fieldName of ["phone", "service_address", "bank_account", "property_clues"]) {
    await expect(page.locator(`[name="${fieldName}"]`)).toHaveAttribute("type", "text");
  }
  await expect(page.getByRole("button", { name: /显示(?:联系电话|送达地址|收款账户|已知财产线索)/ })).toHaveCount(0);

  let releaseSave = () => {};
  const saveGate = new Promise<void>((resolve) => {
    releaseSave = resolve;
  });
  const factsRoute = "**/api/v1/matters/*/facts";
  await page.route(
    factsRoute,
    async (route) => {
      await saveGate;
      await route.continue();
    },
    { times: 1 }
  );
  await page.getByRole("button", { name: "保存并进入检查与预览" }).click();
  await expect(page.getByRole("dialog", { name: "正在保存事项资料" })).toBeVisible();
  await expect(page.getByRole("progressbar")).toBeVisible();
  await expect(applicantName).toBeDisabled();
  releaseSave();
  await expect(page.getByRole("heading", { name: "检查与预览" })).toBeVisible();
  await expect(page.getByRole("dialog")).toBeHidden();

  await expect(page.getByText("生成文件必须由用户自行复核", { exact: false })).toBeVisible();
  const generateButton = page.locator("button").filter({ hasText: "生成并预览申请书" });
  await expect(generateButton).toBeEnabled();

  let releaseGeneration = () => {};
  const generationGate = new Promise<void>((resolve) => {
    releaseGeneration = resolve;
  });
  const generationRoute = "**/api/v1/matters/*/generations";
  await page.route(
    generationRoute,
    async (route) => {
      await generationGate;
      await route.continue();
    },
    { times: 1 }
  );
  await generateButton.click();
  await expect(page.getByRole("dialog", { name: "正在创建预览任务" })).toBeVisible();
  await expect(generateButton).toBeDisabled();
  releaseGeneration();
  await expect(page.getByTitle("强制执行申请书预览")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByRole("dialog")).toBeHidden();

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
