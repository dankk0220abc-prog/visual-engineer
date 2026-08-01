"use client";

import { useTranslations } from "next-intl";

import { StatusPill } from "./status-pill";

export type HealthState = "checking" | "healthy" | "unavailable";

function HealthRow({
  label,
  description,
  state,
}: {
  label: string;
  description: string;
  state: HealthState;
}) {
  const statusT = useTranslations("common.status");
  const display = {
    checking: { label: statusT("checking"), tone: "pending" as const },
    healthy: { label: statusT("healthy"), tone: "positive" as const },
    unavailable: {
      label: statusT("unavailable"),
      tone: "negative" as const,
    },
  }[state];

  return (
    <li className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
      <div>
        <p className="text-sm font-semibold text-slate-900">{label}</p>
        <p className="mt-0.5 text-xs text-slate-500">{description}</p>
      </div>
      <StatusPill tone={display.tone}>{display.label}</StatusPill>
    </li>
  );
}

export function HealthPanel({
  live,
  ready,
  onRetry,
}: {
  live: HealthState;
  ready: HealthState;
  onRetry: () => void;
}) {
  const t = useTranslations("health");
  const hasFailure = live === "unavailable" || ready === "unavailable";

  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      aria-labelledby="health-heading"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
            {t("eyebrow")}
          </p>
          <h2
            id="health-heading"
            className="mt-1 text-lg font-semibold text-slate-950"
          >
            {t("title")}
          </h2>
        </div>
        {hasFailure ? (
          <button
            type="button"
            className="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
            onClick={onRetry}
          >
            {t("recheck")}
          </button>
        ) : null}
      </div>
      <ul className="mt-5 divide-y divide-slate-100">
        <HealthRow
          label={t("liveness")}
          description={t("livenessDescription")}
          state={live}
        />
        <HealthRow
          label={t("readiness")}
          description={t("readinessDescription")}
          state={ready}
        />
      </ul>
    </section>
  );
}
