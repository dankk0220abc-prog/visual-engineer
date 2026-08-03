import { expect, type BrowserContext, type Page } from "@playwright/test";

export const UI_LOCALES = ["en-US", "zh-CN"] as const;
export type UiLocale = (typeof UI_LOCALES)[number];

function browserOrigin(): URL {
  const webPort = process.env.WEB_PORT ?? "3000";
  const origin = new URL(
    process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${webPort}`,
  );
  if (!["127.0.0.1", "localhost"].includes(origin.hostname)) {
    throw new Error(
      `Playwright locale Cookie requires a localhost origin, received ${origin.origin}`,
    );
  }
  return origin;
}

export async function setUiLocale(
  context: BrowserContext,
  locale: UiLocale,
): Promise<void> {
  const navigatedPage = context
    .pages()
    .find((page) => page.url() !== "about:blank");
  if (navigatedPage) {
    throw new Error(
      `UI locale must be established before first navigation, received ${navigatedPage.url()}`,
    );
  }

  const existingPage = context.pages()[0];
  const localeProbe = existingPage ?? (await context.newPage());
  const contextLocale = await localeProbe.evaluate(() => navigator.language);
  if (!existingPage) await localeProbe.close();
  if (contextLocale !== locale) {
    throw new Error(
      `Playwright browser context locale is ${contextLocale}; expected ${locale}`,
    );
  }

  const origin = browserOrigin();
  await context.addCookies([
    {
      name: "ve_locale",
      value: locale,
      domain: origin.hostname,
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);

  const cookie = (await context.cookies(origin.origin)).find(
    (candidate) => candidate.name === "ve_locale",
  );
  if (
    !cookie ||
    cookie.value !== locale ||
    cookie.domain.replace(/^\./, "") !== origin.hostname ||
    cookie.path !== "/"
  ) {
    throw new Error("ve_locale Cookie does not match the localhost test scope");
  }
}

export async function expectUiLocale(
  page: Page,
  locale: UiLocale,
): Promise<void> {
  await expect(page.locator("html")).toHaveAttribute("lang", locale);
  await expect(
    page.getByRole("combobox", {
      name: locale === "zh-CN" ? "界面语言" : "Interface language",
    }),
  ).toHaveValue(locale);

  const origin = browserOrigin();
  const cookie = (await page.context().cookies(origin.origin)).find(
    (candidate) => candidate.name === "ve_locale",
  );
  expect(cookie?.value).toBe(locale);
  expect(cookie?.domain.replace(/^\./, "")).toBe(origin.hostname);
  expect(cookie?.path).toBe("/");
}

export async function switchUiLocale(
  page: Page,
  locale: UiLocale,
): Promise<void> {
  const currentLocale = locale === "zh-CN" ? "Interface language" : "界面语言";
  const navigation = page.waitForNavigation({ waitUntil: "domcontentloaded" });
  await page
    .getByRole("combobox", { name: currentLocale })
    .selectOption(locale);
  await navigation;
  await expectUiLocale(page, locale);
}
