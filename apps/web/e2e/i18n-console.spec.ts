import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";

const dashboardLongTitleTask = {
  title:
    "Localization dashboard task card with an intentionally long title that must remain fully readable at 390 pixel viewport",
  objective:
    "Keep every word in this real task objective readable while the dashboard card wraps naturally within the narrow viewport.",
  repository_kind: "local_path",
  repository_display_name: "Synthetic adversarial fixture",
  repository_locator: "/repositories/e2e/adversarial",
} as const;

type DashboardTask = typeof dashboardLongTitleTask & {
  id: string;
  status: string;
  created_at: string;
};

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

async function createDashboardLongTitleTask(request: APIRequestContext) {
  const apiBaseUrl = process.env.PLAYWRIGHT_API_BASE_URL!;
  const response = await request.post(`${apiBaseUrl}/api/v1/tasks`, {
    data: dashboardLongTitleTask,
    headers: {
      "Idempotency-Key": "i18n-dashboard-long-title-containment-v1",
    },
  });

  expect(response.ok()).toBe(true);
  return (await response.json()) as DashboardTask;
}

async function expectDashboardLongTitleTaskContained(
  page: Page,
  task: DashboardTask,
  locale: "zh-CN" | "en-US",
) {
  await expectLocale(page, locale);
  const card = page
    .getByRole("article")
    .filter({
      has: page.getByRole("heading", { name: task.title, exact: true }),
    })
    .first();
  const title = card.getByRole("heading", { name: task.title, exact: true });
  const objective = card.getByText(task.objective, { exact: true });

  await expect(card).toBeVisible();
  await expect(title).toHaveText(task.title);
  await expect(objective).toHaveText(task.objective);
  await expect(card.getByRole("link")).toHaveAttribute(
    "href",
    `/tasks/${task.id}`,
  );
  await expect(card.locator("time")).toHaveAttribute(
    "datetime",
    task.created_at,
  );

  const layout = await card.evaluate((element) => {
    const cardRect = element.getBoundingClientRect();
    const titleElement = element.querySelector("h3")!;
    const objectiveElement = Array.from(element.querySelectorAll("p")).at(-1)!;
    const titleStyle = getComputedStyle(titleElement);
    const objectiveStyle = getComputedStyle(objectiveElement);
    const titleRange = document.createRange();
    titleRange.selectNodeContents(titleElement);

    return {
      innerWidth: window.innerWidth,
      pageScrollWidth: document.documentElement.scrollWidth,
      cardLeft: cardRect.left,
      cardRight: cardRect.right,
      cardScrollWidth: element.scrollWidth,
      cardClientWidth: element.clientWidth,
      titleLineCount: new Set(
        Array.from(titleRange.getClientRects()).map((rect) =>
          Math.round(rect.top),
        ),
      ).size,
      titleWhiteSpace: titleStyle.whiteSpace,
      titleTextOverflow: titleStyle.textOverflow,
      objectiveLineClamp: objectiveStyle.webkitLineClamp,
    };
  });

  expect(layout.innerWidth).toBe(390);
  expect(layout.pageScrollWidth).toBeLessThanOrEqual(layout.innerWidth);
  expect(layout.cardLeft).toBeGreaterThanOrEqual(0);
  expect(Math.ceil(layout.cardRight)).toBeLessThanOrEqual(layout.innerWidth);
  expect(layout.cardScrollWidth).toBeLessThanOrEqual(layout.cardClientWidth);
  expect(layout.titleLineCount).toBeGreaterThan(1);
  expect(layout.titleWhiteSpace).toBe("normal");
  expect(layout.titleTextOverflow).not.toBe("ellipsis");
  expect(layout.objectiveLineClamp).toBe("none");

  const detailsLink = card.getByRole("link", {
    name: locale === "zh-CN" ? /查看详情/ : /View details/,
  });
  await expect(detailsLink).toBeVisible();
  await detailsLink.scrollIntoViewIfNeeded();
  await detailsLink.click({ trial: true });
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

test.describe("Dashboard narrow localization containment", () => {
  test("keeps a real long-title task card contained at 390px in both locales", async ({
    context,
    page,
    request,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "narrow-chromium");
    test.skip(
      !process.env.PLAYWRIGHT_API_BASE_URL,
      "Requires the real VisualEngineer API",
    );

    const task = await createDashboardLongTitleTask(request);
    await context.clearCookies();
    await page.goto("/");
    await expectDashboardLongTitleTaskContained(page, task, "en-US");

    await switchLocale(page, "zh-CN");
    await expectDashboardLongTitleTaskContained(page, task, "zh-CN");
  });
});
