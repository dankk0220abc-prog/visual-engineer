"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { listRepositories, type RepositoryHandle } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { localizeApiError } from "@/lib/localization";

import { StatusPill } from "./status-pill";

export function RepositoryConsole() {
  const locale = useLocale();
  const t = useTranslations("repositoryConsole");
  const commonT = useTranslations("common");
  const errorT = useTranslations("errors");
  const [repositories, setRepositories] = useState<RepositoryHandle[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setState("loading");
    setError("");
    try {
      setRepositories(await listRepositories());
      setState("ready");
    } catch (reason) {
      setError(localizeApiError(reason, errorT));
      setState("error");
    }
  }, [errorT]);

  useEffect(() => {
    let cancelled = false;
    void listRepositories()
      .then((items) => {
        if (cancelled) return;
        setRepositories(items);
        setState("ready");
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setError(localizeApiError(reason, errorT));
        setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [errorT]);

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="border-b border-slate-200 pb-8">
        <p className="text-sm font-semibold tracking-widest text-blue-700 uppercase">
          {t("eyebrow")}
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          {t("title")}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
          {t("description")}
        </p>
      </header>

      {state === "loading" ? (
        <p
          className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600"
          role="status"
        >
          {t("loading")}
        </p>
      ) : null}
      {state === "error" ? (
        <section
          className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <h2 className="font-semibold text-red-950">{t("loadFailed")}</h2>
          <p className="mt-1 text-sm text-red-800">{error}</p>
          <button
            type="button"
            className="mt-4 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none focus-visible:ring-2 focus-visible:ring-red-700"
            onClick={() => void refresh()}
          >
            {commonT("actions.retry")}
          </button>
        </section>
      ) : null}
      {state === "ready" && repositories.length === 0 ? (
        <section className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
          <h2 className="font-semibold text-slate-900">{t("emptyTitle")}</h2>
          <p className="mt-2 text-sm text-slate-600">{t("emptyDescription")}</p>
        </section>
      ) : null}
      {state === "ready" && repositories.length > 0 ? (
        <ul className="mt-8 grid gap-5 lg:grid-cols-2">
          {repositories.map((repository) => (
            <li
              key={repository.id}
              className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-slate-950">
                    {repository.display_name}
                  </h2>
                  <p className="mt-1 font-mono text-xs break-all text-slate-500">
                    {repository.opaque_handle}
                  </p>
                </div>
                <StatusPill
                  tone={
                    repository.status === "available"
                      ? "positive"
                      : repository.status === "revoked"
                        ? "negative"
                        : "neutral"
                  }
                >
                  {repository.status}
                </StatusPill>
              </div>
              {repository.source_status === "unknown" ? (
                <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                  {t("unknownSource", {
                    count: repository.dirty_path_count,
                  })}
                </p>
              ) : null}
              <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-semibold text-slate-500">
                    {commonT("fields.runner")}
                  </dt>
                  <dd className="mt-1 text-slate-900">
                    {repository.runner_display_name}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-slate-500">
                    {commonT("fields.branch")}
                  </dt>
                  <dd className="mt-1 text-slate-900">
                    {repository.current_branch ?? t("detached")}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-semibold text-slate-500">
                    {commonT("fields.currentRevision")}
                  </dt>
                  <dd className="mt-1 font-mono text-xs break-all text-slate-900">
                    {repository.current_revision ?? t("unavailable")}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-semibold text-slate-500">
                    {commonT("fields.capabilities")}
                  </dt>
                  <dd className="mt-1 break-words text-slate-900">
                    {repository.capabilities.join(" · ")}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-semibold text-slate-500">
                    {commonT("fields.lastVerified")}
                  </dt>
                  <dd className="mt-1 text-slate-900">
                    {repository.last_verified_at
                      ? formatTimestamp(repository.last_verified_at, locale)
                      : commonT("state.notVerified")}
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  );
}
