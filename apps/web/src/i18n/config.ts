export const supportedLocales = ["zh-CN", "en-US"] as const;

export type AppLocale = (typeof supportedLocales)[number];

export const defaultLocale: AppLocale = "en-US";
export const localeCookieName = "ve_locale";
export const localeCookieMaxAge = 60 * 60 * 24 * 365;

export function isAppLocale(value: unknown): value is AppLocale {
  return (
    typeof value === "string" && supportedLocales.includes(value as AppLocale)
  );
}

export function detectLocale(acceptLanguage: string | null): AppLocale {
  if (!acceptLanguage) return defaultLocale;

  const accepted = acceptLanguage
    .split(",")
    .map((item, index) => {
      const [tag = "", ...parameters] = item.trim().split(";");
      const qualityParameter = parameters.find((parameter) =>
        parameter.trim().startsWith("q="),
      );
      const parsedQuality = qualityParameter
        ? Number(qualityParameter.trim().slice(2))
        : 1;

      return {
        tag: tag.toLowerCase(),
        quality: Number.isFinite(parsedQuality) ? parsedQuality : 0,
        index,
      };
    })
    .filter(({ tag, quality }) => Boolean(tag) && quality > 0)
    .sort(
      (left, right) => right.quality - left.quality || left.index - right.index,
    );

  for (const { tag } of accepted) {
    if (tag === "zh" || tag.startsWith("zh-")) return "zh-CN";
    if (tag === "en" || tag.startsWith("en-")) return "en-US";
    if (tag === "*") return defaultLocale;
  }

  return defaultLocale;
}

export function resolveLocale(
  cookieValue: string | undefined,
  acceptLanguage: string | null,
): AppLocale {
  return isAppLocale(cookieValue) ? cookieValue : detectLocale(acceptLanguage);
}
