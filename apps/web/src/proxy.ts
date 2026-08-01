import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  isAppLocale,
  localeCookieMaxAge,
  localeCookieName,
  resolveLocale,
} from "@/i18n/config";

export function proxy(request: NextRequest) {
  const cookieLocale = request.cookies.get(localeCookieName)?.value;
  if (isAppLocale(cookieLocale)) return NextResponse.next();

  const response = NextResponse.next();
  response.cookies.set({
    name: localeCookieName,
    value: resolveLocale(undefined, request.headers.get("accept-language")),
    httpOnly: true,
    sameSite: "lax",
    secure: request.nextUrl.protocol === "https:",
    path: "/",
    maxAge: localeCookieMaxAge,
  });
  return response;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
