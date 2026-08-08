import AxeBuilder from "@axe-core/playwright";
import { randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import type { Locator, Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import type { E2eTestResources } from "./support/isolation";
import { uniqueE2eLabel } from "./support/isolation";
import { expectUiLocale, setUiLocale, switchUiLocale } from "./support/locale";
import { enforceProviderEvidenceSafety } from "../src/lib/provider-evidence-safety";

const repositoryLocator = "/repositories/e2e/adversarial";
const apiBaseUrl = (
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:18000"
).replace(/\/+$/, "");
const captureEvidence = process.env.CAPTURE_PROVIDER_EVIDENCE === "1";
const evidenceDirectory = path.resolve(
  process.env.PLAYWRIGHT_REPOSITORY_ROOT ??
    path.resolve(process.cwd(), "../.."),
  "docs/evidence/provider-foundation",
);
test.use({ locale: "zh-CN" });

async function createSnapshotReadyRun(
  page: Page,
  resources: E2eTestResources,
  testLabel: string,
): Promise<string> {
  await page.goto("/");
  await expectUiLocale(page, "zh-CN");
  await page.getByLabel("任务标题").fill(testLabel);
  await page
    .getByLabel("任务目标")
    .fill(
      "Inspect the fixed model-neutral provider registry without execution authority.",
    );
  await page.getByLabel("显示名称").fill("Synthetic provider fixture");
  await page.getByLabel("仓库位置").fill(repositoryLocator);
  await page.getByRole("button", { name: "创建任务" }).click();
  const taskCard = page
    .getByRole("article")
    .filter({ has: page.getByRole("heading", { name: testLabel }) });
  await taskCard.getByRole("link", { name: /查看详情/ }).click();
  const [runResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        /\/api\/v1\/tasks\/[0-9a-f-]+\/runs$/.test(response.url()) &&
        response.ok(),
    ),
    page.getByRole("button", { name: "启动只读调查" }).click(),
  ]);
  const run: unknown = await runResponse.json();
  if (
    typeof run !== "object" ||
    run === null ||
    !("id" in run) ||
    typeof run.id !== "string"
  ) {
    throw new Error("Created provider-foundation Run response is invalid");
  }
  resources.trackRun(run.id);
  await page.getByRole("link", { name: "打开 Run" }).click();
  await page.getByRole("button", { name: "创建 committed-HEAD 快照" }).click();
  await expect(page.getByRole("heading", { name: "仓库智能" })).toBeVisible();
  await expect(
    page.getByRole("radio", { name: "选择 Deterministic Fixture" }),
  ).toBeVisible();
  return run.id;
}

async function assertAccessibleAndContained(page: Page) {
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
}

async function assertVisibleEvidenceSafe(page: Page) {
  const visibleText = await page.locator("body").innerText();
  const forbiddenPatterns = [
    /\bAuthorization\b/i,
    /Bearer\s+[A-Za-z0-9._~+/-]{8,}/i,
    /\/(?:Users|home)\/[A-Za-z0-9._-]+\//,
    /\bsk-[A-Za-z0-9_-]{16,}\b/,
    /\bAKIA[A-Z0-9]{16}\b/,
    /\bAIza[A-Za-z0-9_-]{20,}\b/,
    /\b(?:ghp|github_pat|xox[baprs])_[A-Za-z0-9_-]{12,}\b/,
    /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  ];
  return enforceProviderEvidenceSafety(visibleText, {
    forbiddenPatterns,
    secretValues: [],
  });
}

async function captureScreenshot(
  page: Page,
  target: Page | Locator,
  filename: string,
) {
  if (!captureEvidence) return;
  const safetyRecord = await assertVisibleEvidenceSafe(page);
  await mkdir(evidenceDirectory, { recursive: true });
  await target.screenshot({
    path: path.join(evidenceDirectory, filename),
    animations: "disabled",
  });
  const scenarioId = filename.replace(/\.png$/, "");
  await writeFile(
    path.join(evidenceDirectory, `${scenarioId}.capture-safety.json`),
    `${JSON.stringify(safetyRecord, null, 2)}\n`,
    "utf8",
  );
}

test.describe("Model-neutral provider foundation", () => {
  test("status registry is bilingual, accessible, and explicit about non-live evidence", async ({
    context,
    page,
  }, testInfo) => {
    await setUiLocale(context, "zh-CN");
    await page.goto("/providers");
    await expect(page.getByText("共 6 个 Provider")).toBeVisible();

    if (testInfo.project.name === "desktop-chromium") {
      await switchUiLocale(page, "en-US");
      await expect(page.getByText("6 providers")).toBeVisible();
    }

    await expect(
      page.getByRole("heading", { name: "Deterministic Fixture", exact: true }),
    ).toBeVisible();
    const providerNames =
      testInfo.project.name === "desktop-chromium"
        ? [
            "Zhipu GLM · 智谱 GLM",
            "Qwen · 通义千问",
            "DeepSeek",
            "Doubao · 豆包",
            "Kimi",
          ]
        : [
            "智谱 GLM · Zhipu GLM",
            "通义千问 · Qwen",
            "DeepSeek",
            "豆包 · Doubao",
            "Kimi",
          ];
    for (const providerName of providerNames) {
      await expect(
        page.getByRole("heading", { name: providerName, exact: true }),
      ).toBeVisible();
    }
    await expect(
      page.getByText(
        testInfo.project.name === "desktop-chromium"
          ? "Fixture / Mock Evidence · Not a live-provider call"
          : "Fixture / Mock 证据 · 非真实 Provider 调用",
      ),
    ).toBeVisible();
    await assertAccessibleAndContained(page);
    await captureScreenshot(
      page,
      page,
      testInfo.project.name === "desktop-chromium"
        ? "provider-registry-desktop-en.png"
        : "provider-registry-mobile-zh.png",
    );
  });

  test("selector defaults to fixture and tampered real-provider submission fails closed", async ({
    context,
    page,
    resources,
  }, testInfo) => {
    await setUiLocale(context, "zh-CN");
    const runId = await createSnapshotReadyRun(
      page,
      resources,
      uniqueE2eLabel(testInfo, "Provider foundation"),
    );
    if (testInfo.project.name === "narrow-chromium") {
      await switchUiLocale(page, "en-US");
    }

    const english = testInfo.project.name === "narrow-chromium";
    const selector = page.locator("section").filter({
      has: page.getByRole("heading", {
        name: english ? "Governed AI Plan is empty" : "受治理 AI 计划为空",
      }),
    });
    const fixture = selector.getByRole("radio", {
      name: english
        ? "Select Deterministic Fixture"
        : "选择 Deterministic Fixture",
    });
    await expect(selector.getByRole("radio")).toHaveCount(6);
    await expect(fixture).toBeChecked();
    await expect(fixture).toBeEnabled();
    const zhipu = selector.getByRole("radio", {
      name: english
        ? "Select Zhipu GLM · 智谱 GLM"
        : "选择 智谱 GLM · Zhipu GLM",
    });
    await expect(zhipu).toBeDisabled();
    const unavailableProviderNames = english
      ? ["Qwen · 通义千问", "DeepSeek", "Doubao · 豆包", "Kimi"]
      : ["通义千问 · Qwen", "DeepSeek", "豆包 · Doubao", "Kimi"];
    for (const providerName of unavailableProviderNames) {
      await expect(
        selector.getByRole("radio", {
          name: english ? `Select ${providerName}` : `选择 ${providerName}`,
        }),
      ).toBeDisabled();
    }

    await assertAccessibleAndContained(page);
    await captureScreenshot(
      page,
      selector,
      testInfo.project.name === "desktop-chromium"
        ? "provider-selector-desktop-zh.png"
        : "provider-selector-mobile-en.png",
    );

    await zhipu.evaluate((control: HTMLInputElement) => {
      control.disabled = false;
      control.click();
    });
    const [deniedResponse] = await Promise.all([
      page.waitForResponse(
        (response) =>
          response.request().method() === "POST" &&
          response.url().endsWith(`/api/v1/runs/${runId}/ai-plan-requests`),
      ),
      selector
        .getByRole("button", {
          name: english ? "Generate governed AI Plan" : "生成受治理 AI 计划",
        })
        .click(),
    ]);
    expect(deniedResponse.status()).toBe(422);
    const deniedBody: unknown = await deniedResponse.json();
    expect(deniedBody).toMatchObject({
      error: {
        code: expect.stringMatching(/^provider_(?:disabled|not_configured)$/),
      },
    });
    const safeError = page.locator('[role="alert"]').filter({
      hasText: english
        ? /This provider (?:is registered|is unavailable)/
        : /此 Provider/,
    });
    await expect(safeError).toHaveCount(1);
    await expect(safeError).toBeVisible();
    if (testInfo.project.name === "desktop-chromium") {
      await captureScreenshot(
        page,
        safeError,
        "provider-unconfigured-error-desktop-zh.png",
      );
    }

    const persisted = await page.request.get(
      `${apiBaseUrl}/api/v1/runs/${runId}/ai-plan-requests`,
      { headers: { "X-Request-ID": randomUUID() } },
    );
    expect(persisted.ok()).toBe(true);
    expect(await persisted.json()).toMatchObject({ items: [], total: 0 });
    await expect(
      page.getByRole("heading", {
        name: english ? "Governed AI Plan is empty" : "受治理 AI 计划为空",
      }),
    ).toBeVisible();
    await assertAccessibleAndContained(page);
  });
});
