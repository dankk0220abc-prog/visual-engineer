"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ApiError, getTask, type Task } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";

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
  const [task, setTask] = useState<Task | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setState("loading");
    setMessage("");
    try {
      setTask(await getTask(taskId));
      setState("ready");
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "出现未预期的错误，请重试。",
      );
      setState("error");
    }
  }, [taskId]);

  useEffect(() => {
    let cancelled = false;

    void getTask(taskId)
      .then((loadedTask) => {
        if (cancelled) return;
        setTask(loadedTask);
        setState("ready");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setMessage(
          error instanceof ApiError
            ? error.message
            : "出现未预期的错误，请重试。",
        );
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [taskId]);

  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
      <Link
        className="inline-flex rounded-lg px-2 py-1 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
        href="/"
      >
        <span aria-hidden="true">←&nbsp;</span>
        返回任务列表
      </Link>

      {state === "loading" ? (
        <div
          className="mt-6 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600"
          role="status"
        >
          正在加载任务详情…
        </div>
      ) : null}

      {state === "error" ? (
        <div
          className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <h1 className="text-lg font-semibold text-red-950">
            无法加载任务详情
          </h1>
          <p className="mt-2 text-sm text-red-800">{message}</p>
          <button
            className="mt-4 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
            type="button"
            onClick={() => void load()}
          >
            重试
          </button>
        </div>
      ) : null}

      {state === "ready" && task ? (
        <article className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-6">
            <div className="min-w-0">
              <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
                Task detail
              </p>
              <h1 className="mt-2 text-2xl font-semibold break-words text-slate-950 sm:text-3xl">
                {task.title}
              </h1>
            </div>
            <StatusPill tone="neutral">{task.status}</StatusPill>
          </div>

          <dl className="mt-2">
            <Detail label="Task ID">
              <span className="font-mono text-xs">{task.id}</span>
            </Detail>
            <Detail label="Objective">{task.objective}</Detail>
            <Detail label="Repository">
              {task.repository_display_name} · {task.repository_kind}
            </Detail>
            <Detail label="Locator">
              <span className="font-mono text-xs">
                {task.repository_locator}
              </span>
            </Detail>
            <Detail label="Created">
              <time dateTime={task.created_at}>
                {formatTimestamp(task.created_at)}
              </time>
            </Detail>
            <Detail label="Updated">
              <time dateTime={task.updated_at}>
                {formatTimestamp(task.updated_at)}
              </time>
            </Detail>
            <Detail label="Version">{task.version}</Detail>
          </dl>
        </article>
      ) : null}
    </main>
  );
}
