"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  cancelRunnerJob,
  getRunnerJob,
  listRunnerJobEvents,
  type RunnerJob,
  type RunnerJobEvent,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { localizeApiError } from "@/lib/localization";

import { StatusPill } from "./status-pill";

function message(
  error: unknown,
  errorT: ReturnType<typeof useTranslations>,
  terminalCancel: string,
): string {
  if (error instanceof ApiError) {
    return error.code === "runner_job_terminal"
      ? terminalCancel
      : localizeApiError(error, errorT);
  }
  return errorT("unexpected");
}

function tone(
  state: RunnerJob["state"],
): "neutral" | "positive" | "negative" | "pending" {
  if (state === "succeeded") return "positive";
  if (state === "failed" || state === "cancelled") return "negative";
  if (state === "queued" || state === "cancel_requested") return "pending";
  return "neutral";
}

function terminal(state: RunnerJob["state"]): boolean {
  return state === "succeeded" || state === "failed" || state === "cancelled";
}

export function RunnerJobConsole({ jobId }: { jobId: string }) {
  const locale = useLocale();
  const t = useTranslations("runnerJob");
  const commonT = useTranslations("common");
  const errorT = useTranslations("errors");
  const [job, setJob] = useState<RunnerJob | null>(null);
  const [events, setEvents] = useState<RunnerJobEvent[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [error, setError] = useState("");
  const [isCancelling, setIsCancelling] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [nextJob, nextEvents] = await Promise.all([
        getRunnerJob(jobId),
        listRunnerJobEvents(jobId),
      ]);
      setJob(nextJob);
      setEvents(nextEvents);
      setLoadState("ready");
      setError("");
    } catch (caught) {
      setError(message(caught, errorT, t("terminalCancel")));
      setLoadState("error");
    }
  }, [errorT, jobId, t]);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([getRunnerJob(jobId), listRunnerJobEvents(jobId)])
      .then(([initialJob, initialEvents]) => {
        if (cancelled) return;
        setJob(initialJob);
        setEvents(initialEvents);
        setLoadState("ready");
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        setError(message(caught, errorT, t("terminalCancel")));
        setLoadState("error");
      });
    const timer = window.setInterval(() => {
      void refresh();
    }, 1000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [errorT, jobId, refresh, t]);

  async function cancel() {
    setIsCancelling(true);
    setError("");
    try {
      const updated = await cancelRunnerJob(jobId);
      setJob(updated);
    } catch (caught) {
      setError(message(caught, errorT, t("terminalCancel")));
    } finally {
      setIsCancelling(false);
    }
  }

  if (loadState === "loading") {
    return (
      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div
          className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600"
          role="status"
        >
          {t("loading")}
        </div>
      </main>
    );
  }

  if (loadState === "error" && job === null) {
    return (
      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div
          className="rounded-2xl border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <p className="font-semibold text-red-900">{t("loadFailed")}</p>
          <p className="mt-1 text-sm text-red-800">{error}</p>
          <button
            type="button"
            className="mt-4 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
            onClick={() => void refresh()}
          >
            {commonT("actions.retry")}
          </button>
        </div>
      </main>
    );
  }

  if (job === null) return null;
  const attempts = job.attempts ?? [];
  const progress = events.reduce<number | null>((latest, event) => {
    const candidate = event.metadata.progress_percent;
    return event.event_type === "job_progress" && typeof candidate === "number"
      ? Math.max(latest ?? 0, candidate)
      : latest;
  }, null);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <Link
        href="/runners"
        className="inline-flex rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
      >
        ← {t("back")}
      </Link>
      <header className="mt-4 border-b border-slate-200 pb-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
              {t("eyebrow")}
            </p>
            <h1 className="mt-2 text-2xl font-semibold break-words text-slate-950 sm:text-3xl">
              {job.kind}
            </h1>
            <p className="mt-2 font-mono text-xs break-all text-slate-500">
              {job.id}
            </p>
          </div>
          <StatusPill tone={tone(job.state)}>{job.state}</StatusPill>
        </div>
        {job.state === "cancel_requested" ? (
          <p
            className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
            role="status"
          >
            {t("cancelPending")}
          </p>
        ) : null}
        {error ? (
          <p
            className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
            role="alert"
          >
            {error}
          </p>
        ) : null}
        {(job.state === "leased" ||
          job.state === "running" ||
          job.state === "cancel_requested") && (
          <button
            type="button"
            className="mt-5 rounded-lg bg-red-700 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-red-800 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isCancelling || job.state === "cancel_requested"}
            onClick={() => void cancel()}
          >
            {job.state === "cancel_requested"
              ? t("cancelRequested")
              : isCancelling
                ? t("cancelling")
                : t("cancelJob")}
          </button>
        )}
        {progress !== null ? (
          <div
            className="mt-5 max-w-xl"
            aria-label={t("progressLabel", { progress })}
          >
            <div className="flex items-center justify-between gap-3 text-xs font-semibold text-slate-700">
              <span>{t("progress")}</span>
              <span>{progress}%</span>
            </div>
            <div
              className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress}
            >
              <div
                className="h-full rounded-full bg-blue-700"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        ) : null}
      </header>

      <div className="mt-8 grid items-start gap-6 lg:grid-cols-2">
        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
          aria-labelledby="envelope-heading"
        >
          <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
            {t("policyEyebrow")}
          </p>
          <h2
            id="envelope-heading"
            className="mt-1 text-xl font-semibold text-slate-950"
          >
            {t("envelope")}
          </h2>
          <dl className="mt-5 grid gap-x-4 gap-y-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                {t("repository")}
              </dt>
              <dd className="mt-1 font-semibold text-emerald-800">
                {job.permission_envelope.repository_access}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                {t("shell")}
              </dt>
              <dd className="mt-1 font-semibold text-emerald-800">
                {String(job.permission_envelope.shell_access)}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                {t("network")}
              </dt>
              <dd className="mt-1 font-semibold text-emerald-800">
                {job.permission_envelope.network_policy}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                {t("maxRuntime")}
              </dt>
              <dd className="mt-1 text-slate-800">
                {job.permission_envelope.max_runtime_seconds}s
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                {t("lease")}
              </dt>
              <dd className="mt-1 text-slate-800">
                {job.permission_envelope.lease_seconds}s
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-slate-500">
                {t("attempts")}
              </dt>
              <dd className="mt-1 text-slate-800">
                {job.attempt_count}/{job.max_attempts}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs font-semibold text-slate-500">
                {t("policyHash")}
              </dt>
              <dd className="mt-1 font-mono text-xs break-all text-slate-800">
                {job.permission_envelope.policy_hash}
              </dd>
            </div>
          </dl>
        </section>

        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
          aria-labelledby="attempts-heading"
        >
          <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
            {t("executionEyebrow")}
          </p>
          <h2
            id="attempts-heading"
            className="mt-1 text-xl font-semibold text-slate-950"
          >
            {t("attemptsTitle")}
          </h2>
          {attempts.length === 0 ? (
            <p className="mt-5 text-sm text-slate-600">{t("noAttempts")}</p>
          ) : (
            <ol className="mt-5 space-y-3">
              {attempts.map((attempt) => (
                <li
                  key={attempt.id}
                  className="rounded-xl border border-slate-200 p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="font-semibold text-slate-900">
                      {t("attemptNumber", {
                        number: attempt.attempt_number,
                      })}
                    </p>
                    <StatusPill
                      tone={
                        attempt.state === "succeeded"
                          ? "positive"
                          : attempt.state === "failed" ||
                              attempt.state === "lease_expired" ||
                              attempt.state === "cancelled"
                            ? "negative"
                            : "neutral"
                      }
                    >
                      {attempt.state}
                    </StatusPill>
                  </div>
                  <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                    <div>
                      <dt className="font-semibold text-slate-500">
                        {commonT("fields.runner")}
                      </dt>
                      <dd className="mt-1 font-mono break-all text-slate-800">
                        {attempt.runner_id}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        {t("leaseHint")}
                      </dt>
                      <dd className="mt-1 font-mono text-slate-800">
                        {attempt.lease_id_hint}
                      </dd>
                    </div>
                  </dl>
                  {attempt.state === "lease_expired" ? (
                    <p className="mt-3 text-xs font-semibold text-red-700">
                      {t("attemptExpired")}{" "}
                      {job.state === "queued"
                        ? t("requeued")
                        : job.state === "failed"
                          ? t("retryExhausted")
                          : t("advanced")}
                    </p>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>

      <section
        className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
        aria-labelledby="result-heading"
      >
        <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
          {t("evidenceEyebrow")}
        </p>
        <h2
          id="result-heading"
          className="mt-1 text-xl font-semibold text-slate-950"
        >
          {t("result")}
        </h2>
        {job.result ? (
          <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
            {Object.entries(job.result).map(([key, value]) => (
              <div key={key} className="min-w-0">
                <dt className="text-xs font-semibold text-slate-500">{key}</dt>
                <dd className="mt-1 break-words text-slate-800">
                  {Array.isArray(value)
                    ? value.join(" · ")
                    : typeof value === "string" || typeof value === "number"
                      ? String(value)
                      : JSON.stringify(value)}
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-5 text-sm text-slate-600">
            {terminal(job.state) ? t("terminalNoResult") : t("resultPending")}
          </p>
        )}
        {job.error_code ? (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <span className="font-semibold">{t("errorEvidence")}: </span>
            <code>{job.error_code}</code>: {job.error_message}
          </p>
        ) : null}
      </section>

      <section
        className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
        aria-labelledby="timeline-heading"
      >
        <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
          {t("timelineEyebrow")}
        </p>
        <h2
          id="timeline-heading"
          className="mt-1 text-xl font-semibold text-slate-950"
        >
          {t("timeline")}
        </h2>
        {events.length === 0 ? (
          <p className="mt-5 text-sm text-slate-600">{t("noEvents")}</p>
        ) : (
          <ol className="mt-5 space-y-4">
            {events.map((event) => (
              <li
                key={event.id}
                className="grid gap-2 border-l-2 border-blue-200 pl-4 sm:grid-cols-[9rem_1fr]"
              >
                <p className="text-xs text-slate-500">
                  #{event.sequence} ·{" "}
                  {formatTimestamp(event.created_at, locale)}
                </p>
                <div className="min-w-0">
                  <p className="font-semibold text-slate-900">
                    {event.event_type}
                  </p>
                  {Object.keys(event.metadata).length > 0 ? (
                    <pre
                      className="mt-2 max-w-full overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100"
                      tabIndex={0}
                      aria-label={t("eventMetadata", {
                        type: event.event_type,
                      })}
                    >
                      {JSON.stringify(event.metadata, null, 2)}
                    </pre>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </main>
  );
}
