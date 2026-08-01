"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import {
  createTask,
  getHealth,
  listTasks,
  type CreateTaskInput,
  type Task,
} from "@/lib/api";
import { localizeApiError } from "@/lib/localization";

import { HealthPanel, type HealthState } from "./health-panel";
import { StatusPill } from "./status-pill";
import { TaskCard } from "./task-card";
import { TaskForm } from "./task-form";

export function Dashboard() {
  const t = useTranslations("dashboard");
  const commonT = useTranslations("common");
  const errorT = useTranslations("errors");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [listState, setListState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [listError, setListError] = useState("");
  const [live, setLive] = useState<HealthState>("checking");
  const [ready, setReady] = useState<HealthState>("checking");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createdTask, setCreatedTask] = useState<Task | null>(null);

  const refreshTasks = useCallback(async () => {
    setListState("loading");
    setListError("");
    try {
      setTasks(await listTasks());
      setListState("ready");
    } catch (error) {
      setListError(localizeApiError(error, errorT));
      setListState("error");
    }
  }, [errorT]);

  const refreshHealth = useCallback(async () => {
    setLive("checking");
    setReady("checking");

    const [liveResult, readyResult] = await Promise.allSettled([
      getHealth("live"),
      getHealth("ready"),
    ]);

    setLive(liveResult.status === "fulfilled" ? "healthy" : "unavailable");
    setReady(readyResult.status === "fulfilled" ? "healthy" : "unavailable");
  }, []);

  useEffect(() => {
    let cancelled = false;

    void listTasks()
      .then((initialTasks) => {
        if (cancelled) return;
        setTasks(initialTasks);
        setListState("ready");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setListError(localizeApiError(error, errorT));
        setListState("error");
      });

    void Promise.allSettled([getHealth("live"), getHealth("ready")]).then(
      ([liveResult, readyResult]) => {
        if (cancelled) return;
        setLive(liveResult.status === "fulfilled" ? "healthy" : "unavailable");
        setReady(
          readyResult.status === "fulfilled" ? "healthy" : "unavailable",
        );
      },
    );

    return () => {
      cancelled = true;
    };
  }, [errorT]);

  async function handleCreate(input: CreateTaskInput): Promise<boolean> {
    setIsSubmitting(true);
    setCreateError("");
    setCreatedTask(null);

    try {
      const { task } = await createTask(input, crypto.randomUUID());
      setCreatedTask(task);
      setTasks((current) => [
        task,
        ...current.filter((item) => item.id !== task.id),
      ]);
      setListState("ready");
      return true;
    } catch (error) {
      setCreateError(localizeApiError(error, errorT));
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="mb-8 border-b border-slate-200 pb-8 sm:mb-10">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm font-semibold tracking-widest text-blue-700 uppercase">
            {t("eyebrow")}
          </p>
          <span className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-800">
            Phase 2
          </span>
        </div>
        <h1 className="mt-4 max-w-3xl text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          {t("title")}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
          {t("description")}
        </p>
      </header>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(20rem,0.65fr)]">
        <div className="space-y-6">
          <section
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
            aria-labelledby="create-heading"
          >
            <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
              {t("newTaskEyebrow")}
            </p>
            <h2
              id="create-heading"
              className="mt-1 text-xl font-semibold text-slate-950"
            >
              {t("createTitle")}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {t("createDescription")}
            </p>

            {createError ? (
              <div
                className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
                role="alert"
              >
                <p className="font-semibold">{t("createFailed")}</p>
                <p className="mt-1">{createError}</p>
              </div>
            ) : null}

            {createdTask ? (
              <div
                className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"
                role="status"
              >
                <p className="font-semibold">{t("createSucceeded")}</p>
                <dl className="mt-2 grid gap-1 text-xs sm:grid-cols-[5rem_1fr]">
                  <dt className="font-semibold">{commonT("fields.id")}</dt>
                  <dd className="font-mono break-all">{createdTask.id}</dd>
                  <dt className="font-semibold">{commonT("fields.status")}</dt>
                  <dd>
                    <StatusPill tone="neutral">{createdTask.status}</StatusPill>
                  </dd>
                  <dt className="font-semibold">
                    {commonT("fields.repository")}
                  </dt>
                  <dd>{createdTask.repository_display_name}</dd>
                </dl>
              </div>
            ) : null}

            <TaskForm isSubmitting={isSubmitting} onSubmit={handleCreate} />
          </section>
        </div>

        <HealthPanel
          live={live}
          ready={ready}
          onRetry={() => void refreshHealth()}
        />
      </div>

      <section className="mt-8 sm:mt-10" aria-labelledby="tasks-heading">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
              {t("registryEyebrow")}
            </p>
            <h2
              id="tasks-heading"
              className="mt-1 text-xl font-semibold text-slate-950"
            >
              {t("recentTasks")}
            </h2>
          </div>
          {listState === "ready" ? (
            <button
              className="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
              type="button"
              onClick={() => void refreshTasks()}
            >
              {t("refreshList")}
            </button>
          ) : null}
        </div>

        {listState === "loading" ? (
          <div
            className="mt-5 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600"
            role="status"
          >
            {t("loadingTasks")}
          </div>
        ) : null}

        {listState === "error" ? (
          <div
            className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-6"
            role="alert"
          >
            <p className="font-semibold text-red-900">{t("loadFailed")}</p>
            <p className="mt-1 text-sm text-red-800">{listError}</p>
            <button
              className="mt-4 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
              type="button"
              onClick={() => void refreshTasks()}
            >
              {commonT("actions.retry")}
            </button>
          </div>
        ) : null}

        {listState === "ready" && tasks.length === 0 ? (
          <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
            <p className="font-semibold text-slate-800">{t("emptyTitle")}</p>
            <p className="mt-1 text-sm text-slate-600">
              {t("emptyDescription")}
            </p>
          </div>
        ) : null}

        {listState === "ready" && tasks.length > 0 ? (
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {tasks.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}
