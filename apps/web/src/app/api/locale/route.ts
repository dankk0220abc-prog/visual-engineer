import { NextResponse } from "next/server";

import {
  isAppLocale,
  localeCookieMaxAge,
  localeCookieName,
} from "@/i18n/config";

export async function POST(request: Request) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: { code: "invalid_locale_request" } },
      { status: 400 },
    );
  }

  const locale =
    typeof body === "object" && body !== null && "locale" in body
      ? body.locale
      : undefined;
  if (!isAppLocale(locale)) {
    return NextResponse.json(
      { error: { code: "unsupported_locale" } },
      { status: 400 },
    );
  }

  const response = NextResponse.json({ locale });
  response.cookies.set({
    name: localeCookieName,
    value: locale,
    httpOnly: true,
    sameSite: "lax",
    secure: new URL(request.url).protocol === "https:",
    path: "/",
    maxAge: localeCookieMaxAge,
  });
  return response;
}
