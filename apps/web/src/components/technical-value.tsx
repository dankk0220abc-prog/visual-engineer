"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

export function TechnicalValue({
  value,
  visible = 12,
}: {
  value: string;
  visible?: number;
}) {
  const t = useTranslations("technicalValue");
  const [copied, setCopied] = useState(false);
  const shortValue =
    value.length > visible ? `${value.slice(0, visible)}…` : value;

  async function copy() {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <span className="inline-flex max-w-full items-center gap-1.5">
      <code
        className="min-w-0 rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-xs break-all text-slate-700"
        title={value}
      >
        {shortValue}
      </code>
      <button
        type="button"
        className="shrink-0 rounded-md px-1.5 py-1 text-xs font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-1"
        aria-label={t("copyAria", { value: shortValue })}
        onClick={() => void copy()}
      >
        {copied ? t("copied") : t("copy")}
      </button>
    </span>
  );
}
