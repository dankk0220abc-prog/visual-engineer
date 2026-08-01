"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { getTask, listRuns, startRun, type Run, type Task } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { localizeApiError } from "@/lib/localization";

import { StatusPill } from "./status-pill";

function Detail({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border-b border-slate-100 py-4 last:border-0">
      <dt className="text-xs font-semibold tracking-wide text-slate-500 uppercase">
        {label}
      </dt>
      <dd className="mt-1 text-sm leading-6 break-words text-slate-900">
        {children}
      </dd>
    </div>
  );
}

export function TaskDetails({ taskId }: { taskId: string }) {
  const locale = useLocale();
  const t = useTranslations("taskDetails");
  const commonT = useTranslations("common");
  const errorT = useTranslations("errors");
  const [task, setTask] = useState<Task | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  const [startMessage, setStartMessage] = useState("");

  const load = useCallback(async () => {
    setState("loading");
    setMessage("");
    try {
      const [loadedTask, loadedRuns] = await Promise.all([
        getTask(taskId),
        listRuns(taskId),
      ]);
      setTask(loadedTask);
      setRuns(loadedRuns);
      setState("ready");
    } catch (error) {
      setMessage(localizeApiError(error, errorT));
      setState("error");
    }
  }, [errorT, taskId]);

  useEffect(() => {
    let cancelled = false;

    void Promise.all([getTask(taskId), listRuns(taskId)])
      .then(([loadedTask, loadedRuns]) => {
        if (cancelled) return;
        setTask(loadedTask);
        setRuns(loadedRuns);
        setState("ready");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setMessage(localizeApiError(error, errorT));
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [errorT, taskId]);

  async function handleStartRun() {
    setIsStarting(true);
    setStartMessage("");
    try {
      const { run } = await startRun(taskId, crypto.randomUUID());
      setRuns((current) => [
        run,
        ...current.filter((item) => item.id !== run.id),
      ]);
      setStartMessage(t("runCreated"));
    } catch (error) {
      setStartMessage(localizeApiError(error, errorT));
    } finally {
      setIsStarting(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
      <Link
        className="inline-flex rounded-lg px-2 py-1 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
        href="/"
      >
        <span aria-hidden="true">←&nbsp;</span>
        {t("back")}
      </Link>

      {state === "loading" ? (
        <div
          className="mt-6 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600"
          role="status"
        >
          {t("loading")}
        </div>
      ) : null}

      {state === "error" ? (
        <div
          className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <h1 className="text-lg font-semibold text-red-950">
            {t("loadFailed")}
          </h1>
          <p className="mt-2 text-sm text-red-800">{message}</p>
          <button
            className="mt-4 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
            type="button"
            onClick={() => void load()}
          >
            {commonT("actions.retry")}
          </button>
        </div>
      ) : null}

      {state === "ready" && task ? (
        <div className="space-y-6">
          <article className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-6">
              <div className="min-w-0">
                <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
                  {t("eyebrow")}
                </p>
                <h1 className="mt-2 text-2xl font-semibold break-words text-slate-950 sm:text-3xl">
                  {task.title}
                </h1>
              </div>
              <StatusPill tone="neutral">{task.status}</StatusPill>
            </div>

            <dl className="mt-2">
              <Detail label={t("taskId")}>
                <span className="font-mono text-xs">{task.id}</span>
              </Detail>
              <Detail label={t("objective")}>{task.objective}</Detail>
              <Detail label={t("repository")}>
                {task.repository_display_name} · {task.repository_kind}
              </Detail>
              <Detail label={t("locator")}>
                <span className="font-mono text-xs">
                  {task.repository_locator}
                </span>
              </Detail>
              <Detail label={t("created")}>
                <time dateTime={task.created_at}>
                  {formatTimestamp(task.created_at, locale)}
                </time>
              </Detail>
              <Detail label={t("updated")}>
                <time dateTime={task.updated_at}>
                  {formatTimestamp(task.updated_at, locale)}
                </time>
              </Detail>
              <Detail label={t("version")}>{task.version}</Detail>
            </dl>
          </article>

          <section
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8"
            aria-labelledby="runs-heading"
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
                  {t("runsEyebrow")}
                </p>
                <h2
                  id="runs-heading"
                  className="mt-1 text-xl font-semibold text-slate-950"
                >
                  {t("runsTitle")}
                </h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                  {t("runsDescription")}
                </p>
              </div>
              <button
                type="button"
                disabled={isStarting || task.repository_kind !== "local_path"}
                onClick={() => void handleStartRun()}
                className="inline-flex min-h-11 items-center justify-center rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isStarting ? t("startingRun") : t("startRun")}
              </button>
            </div>

            {startMessage ? (
              <p
                className="mt-4 rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900"
                role="status"
              >
                {startMessage}
              </p>
            ) : null}

            {runs.length === 0 ? (
              <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
                {t("runsEmpty")}
              </div>
            ) : (
              <ul className="mt-5 divide-y divide-slate-100">
                {runs.map((run) => (
                  <li
                    key={run.id}
                    className="flex flex-wrap items-center justify-between gap-3 py-4 first:pt-0 last:pb-0"
                  >
                    <div className="min-w-0">
                      <p className="font-mono text-xs break-all text-slate-500">
                        {run.id}
                      </p>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-700">
                        <StatusPill tone="neutral">{run.status}</StatusPill>
                        <span aria-hidden="true">·</span>
                        <span>
                          {t("permissionSummary", {
                            permission: run.permission_level,
                          })}
                        </span>
                        <span aria-hidden="true">·</span>
                        <span>Committed HEAD</span>
                      </div>
                    </div>
                    <Link
                      className="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                      href={`/runs/${run.id}`}
                    >
                      {t("openRun")}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}
