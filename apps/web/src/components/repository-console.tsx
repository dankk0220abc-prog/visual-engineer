"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, listRepositories, type RepositoryHandle } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";

import { StatusPill } from "./status-pill";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.requestId
      ? `${error.message}（请求 ID：${error.requestId}）`
      : error.message;
  }
  return "无法加载 Repository Handles。";
}

export function RepositoryConsole() {
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
      setError(errorMessage(reason));
      setState("error");
    }
  }, []);

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
        setError(errorMessage(reason));
        setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="border-b border-slate-200 pb-8">
        <p className="text-sm font-semibold tracking-widest text-blue-700 uppercase">
          Runner-local registry
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          Repository Handles
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
          Control Plane 只保存 opaque handle、版本与有界状态。主机路径留在
          Runner 本地配置中，永不由此页面接收或返回。
        </p>
      </header>

      {state === "loading" ? (
        <p
          className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600"
          role="status"
        >
          正在读取 Repository Registry…
        </p>
      ) : null}
      {state === "error" ? (
        <section
          className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <h2 className="font-semibold text-red-950">加载失败</h2>
          <p className="mt-1 text-sm text-red-800">{error}</p>
          <button
            type="button"
            className="mt-4 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none focus-visible:ring-2 focus-visible:ring-red-700"
            onClick={() => void refresh()}
          >
            重试
          </button>
        </section>
      ) : null}
      {state === "ready" && repositories.length === 0 ? (
        <section className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
          <h2 className="font-semibold text-slate-900">
            暂无 Repository Handle
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            启动带只读 fixture mount 的 Runner 后会自动注册。
          </p>
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
                  Source working-tree status is intentionally unknown. Runner
                  不执行源仓库 Git 配置；{repository.dirty_path_count}{" "}
                  是保守上界， Mirror 只导入 committed HEAD objects。
                </p>
              ) : null}
              <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-semibold text-slate-500">Runner</dt>
                  <dd className="mt-1 text-slate-900">
                    {repository.runner_display_name}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-slate-500">Branch</dt>
                  <dd className="mt-1 text-slate-900">
                    {repository.current_branch ?? "detached"}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-semibold text-slate-500">
                    Current revision
                  </dt>
                  <dd className="mt-1 font-mono text-xs break-all text-slate-900">
                    {repository.current_revision ?? "unavailable"}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-semibold text-slate-500">Capabilities</dt>
                  <dd className="mt-1 break-words text-slate-900">
                    {repository.capabilities.join(" · ")}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-semibold text-slate-500">
                    Last verified
                  </dt>
                  <dd className="mt-1 text-slate-900">
                    {repository.last_verified_at
                      ? formatTimestamp(repository.last_verified_at)
                      : "尚未验证"}
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
