"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import {
  createRunnerJob,
  listRunnerJobs,
  listRunners,
  revokeRunner,
  type CreateRunnerJobInput,
  type Runner,
  type RunnerJob,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { localizeApiError } from "@/lib/localization";

import { StatusPill } from "./status-pill";
import { TechnicalValue } from "./technical-value";

function runnerTone(
  status: Runner["status"],
): "neutral" | "positive" | "negative" | "pending" {
  if (status === "online") return "positive";
  if (status === "revoked") return "negative";
  if (status === "registered") return "pending";
  return "neutral";
}

function jobTone(
  state: RunnerJob["state"],
): "neutral" | "positive" | "negative" | "pending" {
  if (state === "succeeded") return "positive";
  if (state === "failed" || state === "cancelled") return "negative";
  if (state === "queued" || state === "cancel_requested") return "pending";
  return "neutral";
}

export function RunnerConsole() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("runnerConsole");
  const commonT = useTranslations("common");
  const errorT = useTranslations("errors");
  const [runners, setRunners] = useState<Runner[]>([]);
  const [jobs, setJobs] = useState<RunnerJob[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [loadError, setLoadError] = useState("");
  const [kind, setKind] = useState<CreateRunnerJobInput["kind"]>(
    "system_diagnostic_v1",
  );
  const [duration, setDuration] = useState(3000);
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchError, setDispatchError] = useState("");
  const [revokingId, setRevokingId] = useState("");

  const refresh = useCallback(
    async (showLoading = true) => {
      if (showLoading) setLoadState("loading");
      setLoadError("");
      try {
        const [nextRunners, nextJobs] = await Promise.all([
          listRunners(),
          listRunnerJobs(),
        ]);
        setRunners(nextRunners);
        setJobs(nextJobs);
        setLoadState("ready");
      } catch (error) {
        setLoadError(localizeApiError(error, errorT));
        setLoadState("error");
      }
    },
    [errorT],
  );

  useEffect(() => {
    let cancelled = false;
    void Promise.all([listRunners(), listRunnerJobs()])
      .then(([initialRunners, initialJobs]) => {
        if (cancelled) return;
        setRunners(initialRunners);
        setJobs(initialJobs);
        setLoadState("ready");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setLoadError(localizeApiError(error, errorT));
        setLoadState("error");
      });
    const timer = window.setInterval(() => {
      void refresh(false);
    }, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [errorT, refresh]);

  async function dispatch() {
    setIsDispatching(true);
    setDispatchError("");
    try {
      const input: CreateRunnerJobInput =
        kind === "system_diagnostic_v1"
          ? { kind: "system_diagnostic_v1" }
          : { kind: "controlled_wait_v1", duration_ms: duration };
      const job = await createRunnerJob(input);
      setJobs((current) => [
        job,
        ...current.filter((item) => item.id !== job.id),
      ]);
      router.push(`/runners/jobs/${job.id}`);
    } catch (error) {
      setDispatchError(localizeApiError(error, errorT));
    } finally {
      setIsDispatching(false);
    }
  }

  async function revoke(runnerId: string) {
    setRevokingId(runnerId);
    try {
      const revoked = await revokeRunner(runnerId);
      setRunners((current) =>
        current.map((item) => (item.id === revoked.id ? revoked : item)),
      );
    } catch (error) {
      setLoadError(localizeApiError(error, errorT));
      setLoadState("error");
    } finally {
      setRevokingId("");
    }
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="border-b border-slate-200 pb-8">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm font-semibold tracking-widest text-blue-700 uppercase">
            {t("eyebrow")}
          </p>
          <span className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-800">
            Phase 3
          </span>
        </div>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          {t("title")}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
          {t("description")}
        </p>
      </header>

      {loadState === "loading" ? (
        <div
          className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600"
          role="status"
        >
          {t("loading")}
        </div>
      ) : null}

      {loadState === "error" ? (
        <div
          className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <p className="font-semibold text-red-900">{t("loadFailed")}</p>
          <p className="mt-1 text-sm text-red-800">{loadError}</p>
          <button
            type="button"
            className="mt-4 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
            onClick={() => void refresh()}
          >
            {commonT("actions.retry")}
          </button>
        </div>
      ) : null}

      {loadState === "ready" ? (
        <>
          {runners.every((runner) => runner.status !== "online") ? (
            <aside
              className="mt-8 rounded-2xl border border-amber-200 bg-amber-50 p-5"
              role="status"
            >
              <p className="font-semibold text-amber-950">
                {t("runnerUnavailableTitle")}
              </p>
              <p className="mt-1 text-sm leading-6 text-amber-900">
                {t("runnerUnavailableDescription")}
              </p>
              <details className="mt-2 text-xs text-amber-900">
                <summary className="cursor-pointer font-semibold outline-none focus-visible:ring-2 focus-visible:ring-amber-700">
                  {t("technicalDetails")}
                </summary>
                <code className="mt-2 block font-mono">runner_offline</code>
              </details>
            </aside>
          ) : null}
          <div className="mt-8 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(20rem,0.8fr)]">
            <section
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
              aria-labelledby="runner-registry-heading"
            >
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
                    {t("registryEyebrow")}
                  </p>
                  <h2
                    id="runner-registry-heading"
                    className="mt-1 text-xl font-semibold text-slate-950"
                  >
                    {t("registryTitle")}
                  </h2>
                </div>
                <button
                  type="button"
                  className="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                  onClick={() => void refresh(false)}
                >
                  {commonT("actions.refresh")}
                </button>
              </div>

              {runners.length === 0 ? (
                <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
                  <p className="font-semibold text-slate-800">
                    {t("emptyRunners")}
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    {t("emptyRunnersHelp")}
                  </p>
                </div>
              ) : (
                <ul className="mt-5 space-y-4">
                  {runners.map((runner) => (
                    <li
                      key={runner.id}
                      className="rounded-xl border border-slate-200 p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-950">
                            {runner.display_name}
                          </p>
                          <div className="mt-1">
                            <TechnicalValue value={runner.id} />
                          </div>
                        </div>
                        <StatusPill tone={runnerTone(runner.status)}>
                          {runner.status}
                        </StatusPill>
                      </div>
                      <dl className="mt-4 grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
                        <div>
                          <dt className="text-xs font-semibold text-slate-500">
                            {t("lastSeen")}
                          </dt>
                          <dd className="mt-1 text-slate-800">
                            {runner.last_seen_at
                              ? formatTimestamp(runner.last_seen_at, locale)
                              : t("neverSeen")}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-xs font-semibold text-slate-500">
                            {t("protocolSoftware")}
                          </dt>
                          <dd className="mt-1 text-slate-800">
                            v{runner.protocol_version} /{" "}
                            {runner.software_version}
                          </dd>
                        </div>
                        <div className="sm:col-span-2">
                          <dt className="text-xs font-semibold text-slate-500">
                            {commonT("fields.capabilities")}
                          </dt>
                          <dd className="mt-1 break-words text-slate-800">
                            {runner.capabilities.join(" · ")}
                          </dd>
                        </div>
                        <div className="sm:col-span-2">
                          <dt className="text-xs font-semibold text-slate-500">
                            {t("activeJob")}
                          </dt>
                          <dd className="mt-1 text-slate-800">
                            {runner.active_job ? (
                              <Link
                                href={`/runners/jobs/${runner.active_job.id}`}
                                className="font-semibold text-blue-700 underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-blue-600"
                              >
                                {runner.active_job.kind} ·{" "}
                                <StatusPill
                                  tone={jobTone(runner.active_job.state)}
                                >
                                  {runner.active_job.state}
                                </StatusPill>
                              </Link>
                            ) : (
                              t("none")
                            )}
                          </dd>
                        </div>
                      </dl>
                      <button
                        type="button"
                        className="mt-4 rounded-lg px-3 py-2 text-sm font-semibold text-red-700 ring-1 ring-red-200 outline-none hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        disabled={
                          runner.status === "revoked" ||
                          revokingId === runner.id
                        }
                        onClick={() => void revoke(runner.id)}
                      >
                        {runner.status === "revoked"
                          ? t("revoked")
                          : revokingId === runner.id
                            ? t("revoking")
                            : t("revokeRunner")}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section
              className="rounded-2xl border border-blue-200 bg-blue-50/60 p-5 shadow-sm sm:p-6"
              aria-labelledby="dispatch-heading"
            >
              <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
                {t("dispatchEyebrow")}
              </p>
              <h2
                id="dispatch-heading"
                className="mt-1 text-xl font-semibold text-slate-950"
              >
                {t("dispatchTitle")}
              </h2>
              <fieldset className="mt-5 space-y-3">
                <legend className="text-sm font-semibold text-slate-800">
                  {t("jobKind")}
                </legend>
                <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-blue-200 bg-white p-3">
                  <input
                    type="radio"
                    name="job-kind"
                    value="system_diagnostic_v1"
                    checked={kind === "system_diagnostic_v1"}
                    onChange={() => setKind("system_diagnostic_v1")}
                    className="mt-1"
                  />
                  <span>
                    <span className="block font-semibold text-slate-900">
                      {t("systemDiagnostic")}
                    </span>
                    <span className="mt-1 block text-xs leading-5 text-slate-600">
                      {t("systemDiagnosticHelp")}
                    </span>
                  </span>
                </label>
                <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-blue-200 bg-white p-3">
                  <input
                    type="radio"
                    name="job-kind"
                    value="controlled_wait_v1"
                    checked={kind === "controlled_wait_v1"}
                    onChange={() => setKind("controlled_wait_v1")}
                    className="mt-1"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block font-semibold text-slate-900">
                      {t("controlledWait")}
                    </span>
                    <span className="mt-1 block text-xs leading-5 text-slate-600">
                      {t("controlledWaitHelp")}
                    </span>
                  </span>
                </label>
              </fieldset>

              {kind === "controlled_wait_v1" ? (
                <label className="mt-4 block text-sm font-semibold text-slate-800">
                  {t("duration")}
                  <input
                    className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-200"
                    type="number"
                    min={100}
                    max={10000}
                    step={100}
                    value={duration}
                    onChange={(event) =>
                      setDuration(Number(event.currentTarget.value))
                    }
                  />
                </label>
              ) : null}

              <div
                className="mt-5 rounded-xl border border-blue-200 bg-white p-4"
                aria-label={t("envelopePreview")}
              >
                <p className="text-sm font-semibold text-slate-950">
                  {t("envelopePreview")}
                </p>
                <dl className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-2 text-xs">
                  <dt className="text-slate-600">{t("allowedCapability")}</dt>
                  <dd className="text-right font-mono break-all text-slate-900">
                    {kind}
                  </dd>
                  <dt className="text-slate-600">{t("repositoryAccess")}</dt>
                  <dd className="font-semibold text-emerald-800">
                    {t("noneValue")}
                  </dd>
                  <dt className="text-slate-600">{t("shellAccess")}</dt>
                  <dd className="font-semibold text-emerald-800">
                    {t("falseValue")}
                  </dd>
                  <dt className="text-slate-600">{t("network")}</dt>
                  <dd className="font-semibold text-emerald-800">
                    {t("controlPlaneOnly")}
                  </dd>
                  <dt className="text-slate-600">{t("maxRuntime")}</dt>
                  <dd className="font-semibold text-slate-900">
                    {t("tenSeconds")}
                  </dd>
                  <dt className="text-slate-600">{t("projectCode")}</dt>
                  <dd className="font-semibold text-emerald-800">
                    {t("notAccessed")}
                  </dd>
                </dl>
              </div>

              {dispatchError ? (
                <p
                  className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
                  role="alert"
                >
                  {dispatchError}
                </p>
              ) : null}

              <button
                type="button"
                className="mt-5 w-full rounded-lg bg-blue-700 px-4 py-3 text-sm font-semibold text-white outline-none hover:bg-blue-800 focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={
                  isDispatching ||
                  runners.every((runner) => runner.status !== "online") ||
                  (kind === "controlled_wait_v1" &&
                    (duration < 100 || duration > 10000))
                }
                onClick={() => void dispatch()}
              >
                {isDispatching ? t("dispatching") : t("createAndView")}
              </button>
              {runners.every((runner) => runner.status !== "online") ? (
                <p className="mt-2 text-xs text-amber-800">
                  {t("noOnlineRunner")}
                </p>
              ) : null}
            </section>
          </div>

          <section className="mt-8" aria-labelledby="runner-jobs-heading">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
                  {t("queueEyebrow")}
                </p>
                <h2
                  id="runner-jobs-heading"
                  className="mt-1 text-xl font-semibold text-slate-950"
                >
                  {t("recentJobs")}
                </h2>
              </div>
            </div>
            {jobs.length === 0 ? (
              <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
                <p className="font-semibold text-slate-800">{t("emptyJobs")}</p>
                <p className="mt-1 text-sm text-slate-600">
                  {t("emptyJobsHelp")}
                </p>
              </div>
            ) : (
              <ul className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {jobs.map((job) => (
                  <li
                    key={job.id}
                    className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <p className="font-semibold break-words text-slate-950">
                        {job.kind}
                      </p>
                      <StatusPill tone={jobTone(job.state)}>
                        {job.state}
                      </StatusPill>
                    </div>
                    <div className="mt-2">
                      <TechnicalValue value={job.id} />
                    </div>
                    {job.result_projection_status === "incompatible_legacy" ? (
                      <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
                        {t("legacyResultUnavailable")}
                      </p>
                    ) : null}
                    <p className="mt-3 text-sm text-slate-600">
                      {t("attempts", {
                        current: job.attempt_count,
                        maximum: job.max_attempts,
                      })}{" "}
                      · {formatTimestamp(job.created_at, locale)}
                    </p>
                    <Link
                      href={`/runners/jobs/${job.id}`}
                      className="mt-4 inline-flex rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                    >
                      {t("viewJob")}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </main>
  );
}
