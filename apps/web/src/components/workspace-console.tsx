"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  createWorkspace,
  listExecutionGrants,
  listWorkspaces,
  type ExecutionGrant,
  type Workspace,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";

import { StatusPill } from "./status-pill";

function message(error: unknown): string {
  if (error instanceof ApiError) return `${error.code}: ${error.message}`;
  return "无法加载 Workspace。";
}

function workspaceTone(
  state: Workspace["state"],
): "neutral" | "positive" | "negative" | "pending" {
  if (state === "ready" || state === "rolled_back") return "positive";
  if (
    state === "requested" ||
    state === "preparing" ||
    state === "sealing" ||
    state === "rollback_requested" ||
    state === "discard_requested"
  )
    return "pending";
  if (state === "failed" || state === "expired") return "negative";
  return "neutral";
}

export function WorkspaceConsole() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [grants, setGrants] = useState<ExecutionGrant[]>([]);
  const [selectedGrant, setSelectedGrant] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(async (showLoading = false) => {
    if (showLoading) setState("loading");
    try {
      const [nextWorkspaces, nextGrants] = await Promise.all([
        listWorkspaces(),
        listExecutionGrants(),
      ]);
      setWorkspaces(nextWorkspaces);
      setGrants(nextGrants);
      const approved = nextGrants.find((grant) => grant.status === "approved");
      setSelectedGrant((current) => current || approved?.id || "");
      setState("ready");
      setError("");
    } catch (reason) {
      setError(message(reason));
      setState("error");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([listWorkspaces(), listExecutionGrants()])
      .then(([nextWorkspaces, nextGrants]) => {
        if (cancelled) return;
        setWorkspaces(nextWorkspaces);
        setGrants(nextGrants);
        setSelectedGrant(
          nextGrants.find((grant) => grant.status === "approved")?.id || "",
        );
        setState("ready");
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setError(message(reason));
        setState("error");
      });
    const timer = window.setInterval(() => void refresh(false), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [refresh]);

  const approvedGrants = useMemo(
    () => grants.filter((grant) => grant.status === "approved"),
    [grants],
  );

  async function create() {
    if (!selectedGrant) return;
    setCreating(true);
    setError("");
    try {
      const action = await createWorkspace(selectedGrant);
      router.push(`/workspaces/${action.workspace.id}`);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="border-b border-slate-200 pb-8">
        <p className="text-sm font-semibold tracking-widest text-blue-700 uppercase">
          Runner-owned execution surface
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          Isolated Workspaces
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
          所有修改只发生在 Runner volume 中的 detached worktree。Control Plane
          不保存绝对路径，源仓库保持只读。
        </p>
      </header>

      {error ? (
        <div
          className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900"
          role="alert"
        >
          {error}
          <button
            type="button"
            className="ml-3 font-semibold underline"
            onClick={() => void refresh(true)}
          >
            重试
          </button>
        </div>
      ) : null}
      {state === "loading" ? (
        <p className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">
          正在加载 Workspaces…
        </p>
      ) : null}
      {state === "ready" ? (
        <>
          <section className="mt-8 rounded-2xl border border-blue-200 bg-blue-50/60 p-5 sm:p-6">
            <h2 className="text-xl font-semibold text-slate-950">
              创建 exact-revision Workspace
            </h2>
            {approvedGrants.length === 0 ? (
              <p className="mt-3 text-sm text-slate-700">
                没有可用的 approved Execution Grant。请先在{" "}
                <Link
                  href="/execution-grants"
                  className="font-semibold text-blue-800 underline"
                >
                  Execution Grants
                </Link>{" "}
                完成独立批准。
              </p>
            ) : (
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
                <label className="min-w-0 flex-1 text-sm font-semibold text-slate-800">
                  Approved Grant
                  <select
                    className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-200"
                    value={selectedGrant}
                    onChange={(event) =>
                      setSelectedGrant(event.currentTarget.value)
                    }
                  >
                    {approvedGrants.map((grant) => (
                      <option key={grant.id} value={grant.id}>
                        {grant.repository_display_name} · {grant.id.slice(0, 8)}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2 disabled:opacity-50"
                  disabled={!selectedGrant || creating}
                  onClick={() => void create()}
                >
                  {creating ? "请求中…" : "Prepare Workspace"}
                </button>
              </div>
            )}
          </section>

          {workspaces.length === 0 ? (
            <section className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
              <h2 className="font-semibold text-slate-900">暂无 Workspace</h2>
              <p className="mt-2 text-sm text-slate-600">
                approved Grant 不会自动执行；必须明确创建 Workspace。
              </p>
            </section>
          ) : (
            <ul className="mt-8 grid gap-5 lg:grid-cols-2">
              {workspaces.map((workspace) => (
                <li
                  key={workspace.id}
                  className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="font-semibold text-slate-950">
                        {workspace.repository_display_name}
                      </h2>
                      <p className="mt-1 font-mono text-xs break-all text-slate-500">
                        {workspace.id}
                      </p>
                    </div>
                    <StatusPill tone={workspaceTone(workspace.state)}>
                      {workspace.state}
                    </StatusPill>
                  </div>
                  <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="font-semibold text-slate-500">Runner</dt>
                      <dd className="mt-1">{workspace.runner_display_name}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">Changed</dt>
                      <dd className="mt-1">
                        {workspace.changed_file_count}/
                        {workspace.max_files_changed} files ·{" "}
                        {workspace.total_written_bytes}/
                        {workspace.max_total_write_bytes} bytes
                      </dd>
                    </div>
                    <div className="sm:col-span-2">
                      <dt className="font-semibold text-slate-500">
                        Source revision
                      </dt>
                      <dd className="mt-1 font-mono text-xs break-all">
                        {workspace.source_revision}
                      </dd>
                    </div>
                  </dl>
                  <p className="mt-4 text-xs text-slate-500">
                    Expires {formatTimestamp(workspace.expires_at)}
                  </p>
                  <Link
                    href={`/workspaces/${workspace.id}`}
                    className="mt-4 inline-flex rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600"
                  >
                    查看 Workspace
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : null}
    </main>
  );
}
