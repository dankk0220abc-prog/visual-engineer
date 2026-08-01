import { expect, test, type Page } from "@playwright/test";

const localizedPages = {
  "en-US": [
    ["/", "Governed frontend delivery task console"],
    ["/repositories", "Repository Intelligence"],
    ["/execution-grants", "Execution Grants"],
    ["/workspaces", "Isolated Workspaces"],
    ["/validations", "Validation Runs"],
    ["/reviews", "Review & Release Readiness"],
    ["/deliveries", "Local Delivery Lifecycle"],
  ],
  "zh-CN": [
    ["/", "受治理的前端交付任务控制台"],
    ["/repositories", "仓库智能"],
    ["/execution-grants", "执行授权"],
    ["/workspaces", "隔离工作区"],
    ["/validations", "验证 Run"],
    ["/reviews", "审查与发布就绪度"],
    ["/deliveries", "本地交付生命周期"],
  ],
} as const;

async function expectLocale(page: Page, locale: "zh-CN" | "en-US") {
  await expect(page.locator("html")).toHaveAttribute("lang", locale);
  await expect(
    page.getByRole("combobox", {
      name: locale === "zh-CN" ? "界面语言" : "Interface language",
    }),
  ).toHaveValue(locale);
}

async function switchLocale(page: Page, locale: "zh-CN" | "en-US") {
  const navigation = page.waitForNavigation({ waitUntil: "domcontentloaded" });
  await page
    .getByRole("combobox", {
      name: locale === "zh-CN" ? "Interface language" : "界面语言",
    })
    .selectOption(locale);
  await navigation;
  await expectLocale(page, locale);
}

async function smokeCorePages(page: Page, locale: "zh-CN" | "en-US") {
  for (const [path, title] of localizedPages[locale]) {
    await page.goto(path);
    await expectLocale(page, locale);
    await expect(
      page.getByRole("heading", { name: title, exact: true }),
    ).toBeVisible();
    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(hasHorizontalOverflow).toBe(false);
  }
}

test.describe("English Web Console localization", () => {
  test.use({ locale: "en-US" });

  test("detects English, keeps it on refresh, and renders core pages", async ({
    context,
    page,
    request,
  }) => {
    await context.clearCookies();
    await page.goto("/");
    await expectLocale(page, "en-US");
    await page.reload();
    await expectLocale(page, "en-US");
    await smokeCorePages(page, "en-US");

    const apiBaseUrl = process.env.PLAYWRIGHT_API_BASE_URL;
    if (apiBaseUrl) {
      const response = await request.get(`${apiBaseUrl}/api/v1/repositories`);
      expect(response.ok()).toBe(true);
      const payload = (await response.json()) as {
        items: Array<{ current_revision: string | null }>;
      };
      const revision = payload.items[0]?.current_revision;
      expect(revision).toBeTruthy();
      await page.goto("/repositories");
      await expect(page.getByText(revision!, { exact: true })).toBeVisible();
    }
  });
});

test.describe("Chinese Web Console localization", () => {
  test.use({ locale: "zh-CN" });

  test("detects Chinese and persists accessible language switches", async ({
    context,
    page,
  }) => {
    await context.clearCookies();
    await page.goto("/");
    await expectLocale(page, "zh-CN");

    await switchLocale(page, "en-US");
    await page.reload();
    await expectLocale(page, "en-US");
    await switchLocale(page, "zh-CN");
    await page.reload();
    await expectLocale(page, "zh-CN");
    await smokeCorePages(page, "zh-CN");
  });
});
