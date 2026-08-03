"use client";

import { useTranslations } from "next-intl";

import { isLocalizedStatus, localizeStatus } from "@/lib/localization";

type StatusTone = "neutral" | "positive" | "negative" | "pending";

const toneClasses: Record<StatusTone, string> = {
  neutral: "border-slate-200 bg-slate-50 text-slate-700",
  positive: "border-emerald-200 bg-emerald-50 text-emerald-800",
  negative: "border-red-200 bg-red-50 text-red-800",
  pending: "border-amber-200 bg-amber-50 text-amber-800",
};

export function StatusPill({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: StatusTone;
}) {
  const t = useTranslations("common.status");
  const content =
    typeof children === "string" &&
    (isLocalizedStatus(children) || /^[a-z][a-z0-9_]*$/.test(children))
      ? localizeStatus(children, t)
      : children;
  const status =
    typeof children === "string" && /^[a-z][a-z0-9_]*$/.test(children)
      ? children
      : undefined;

  return (
    <span
      data-status={status}
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClasses[tone]}`}
    >
      {content}
    </span>
  );
}
