"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { isAppLocale } from "@/i18n/config";

export function LocaleSwitcher() {
  const locale = useLocale();
  const t = useTranslations("localeSwitcher");
  const [isChanging, setIsChanging] = useState(false);
  const [failed, setFailed] = useState(false);

  async function changeLocale(value: string) {
    if (!isAppLocale(value) || value === locale) return;
    setIsChanging(true);
    setFailed(false);

    try {
      const response = await fetch("/api/locale", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ locale: value }),
      });
      if (!response.ok) throw new Error("locale_update_failed");
      window.location.reload();
    } catch {
      setFailed(true);
      setIsChanging(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <label className="sr-only" htmlFor="console-locale">
        {t("label")}
      </label>
      <select
        id="console-locale"
        aria-label={t("label")}
        aria-describedby={failed ? "locale-switch-error" : undefined}
        className="min-h-10 rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm font-semibold text-slate-700 outline-none hover:border-slate-400 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-60"
        value={locale}
        disabled={isChanging}
        onChange={(event) => void changeLocale(event.currentTarget.value)}
      >
        <option value="zh-CN">中文</option>
        <option value="en-US">English</option>
      </select>
      {isChanging ? (
        <span className="sr-only" role="status">
          {t("changing")}
        </span>
      ) : null}
      {failed ? (
        <span id="locale-switch-error" className="sr-only" role="alert">
          {t("error")}
        </span>
      ) : null}
    </div>
  );
}
