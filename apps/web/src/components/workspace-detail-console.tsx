"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  discardWorkspace,
  getRunnerJob,
  getWorkspace,
  getWorkspaceDiff,
  getWorkspaceStatus,
  listWorkspaceCheckpoints,
  listWorkspaceDirectory,
  listWorkspaceEvents,
  readWorkspaceText,
  rollbackWorkspace,
  writeWorkspaceText,
  type RunnerJob,
  type Workspace,
  type WorkspaceCheckpoint,
  type WorkspaceEntry,
  type WorkspaceEvent,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";

import { StatusPill } from "./status-pill";

function message(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.code}: ${error.message}${
      error.requestId ? `（请求 ID：${error.requestId}）` : ""
    }`;
  }
  if (error instanceof Error) return error.message;
  return "Workspace 操作失败。";
}

function tone(
  state: Workspace["state"],
): "neutral" | "positive" | "negative" | "pending" {
  if (state === "ready" || state === "rolled_back") return "positive";
  if (state === "failed" || state === "expired") return "negative";
  if (
    state === "requested" ||
    state === "preparing" ||
    state === "sealing" ||
    state === "rollback_requested" ||
    state === "discard_requested"
  )
    return "pending";
  return "neutral";
}

async function waitForJob(jobId: string): Promise<RunnerJob> {
  for (let attempt = 0; attempt < 240; attempt += 1) {
    const job = await getRunnerJob(jobId);
    if (["succeeded", "failed", "cancelled"].includes(job.state)) return job;
    await new Promise((resolve) => window.setTimeout(resolve, 500));
  }
  throw new Error("Job 等待超时；请刷新后查看 durable 状态。");
}

export function WorkspaceDetailConsole({
  workspaceId,
}: {
  workspaceId: string;
}) {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [events, setEvents] = useState<WorkspaceEvent[]>([]);
  const [checkpoints, setCheckpoints] = useState<WorkspaceCheckpoint[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [lastJob, setLastJob] = useState<RunnerJob | null>(null);
  const [directory, setDirectory] = useState("sandbox");
  const [entries, setEntries] = useState<WorkspaceEntry[]>([]);
  const [readPath, setReadPath] = useState("sandbox/original.txt");
  const [readContent, setReadContent] = useState("");
  const [currentHash, setCurrentHash] = useState("");
  const [writeMode, setWriteMode] = useState<"create" | "replace">("replace");
  const [writePath, setWritePath] = useState("sandbox/original.txt");
  const [writeContent, setWriteContent] = useState("Updated fixture text.\n");
  const [expectedHash, setExpectedHash] = useState("");

  const refresh = useCallback(
    async (showLoading = false) => {
      if (showLoading) {
        setState("loading");
        setError("");
      }
      try {
        const [nextWorkspace, nextEvents, nextCheckpoints] = await Promise.all([
          getWorkspace(workspaceId),
          listWorkspaceEvents(workspaceId),
          listWorkspaceCheckpoints(workspaceId),
        ]);
        setWorkspace(nextWorkspace);
        setEvents(nextEvents);
        setCheckpoints(nextCheckpoints);
        setState("ready");
      } catch (reason) {
        setError(message(reason));
        setState("error");
      }
    },
    [workspaceId],
  );

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      getWorkspace(workspaceId),
      listWorkspaceEvents(workspaceId),
      listWorkspaceCheckpoints(workspaceId),
    ])
      .then(([nextWorkspace, nextEvents, nextCheckpoints]) => {
        if (cancelled) return;
        setWorkspace(nextWorkspace);
        setEvents(nextEvents);
        setCheckpoints(nextCheckpoints);
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
  }, [refresh, workspaceId]);

  const newByteSize = useMemo(
    () => new TextEncoder().encode(writeContent).byteLength,
    [writeContent],
  );
  const remainingBytes = workspace
    ? Math.max(
        0,
        workspace.max_total_write_bytes - workspace.total_written_bytes,
      )
    : 0;

  async function executeAction(
    label: string,
    dispatch: () => Promise<{ job: RunnerJob }>,
  ): Promise<RunnerJob | null> {
    setBusy(label);
    setError("");
    setNotice(`${label} 已排队，等待 Runner lease…`);
    try {
      const action = await dispatch();
      const completed = await waitForJob(action.job.id);
      setLastJob(completed);
      if (completed.state !== "succeeded") {
        throw new Error(
          `${completed.error_code ?? "job_failed"}: Runner 拒绝或未完成该操作。`,
        );
      }
      setNotice(`${label} 已完成并持久化。`);
      await refresh(false);
      return completed;
    } catch (reason) {
      setError(message(reason));
      setNotice("");
      await refresh(false);
      return null;
    } finally {
      setBusy("");
    }
  }

  async function runList() {
    const completed = await executeAction("List", () =>
      listWorkspaceDirectory(workspaceId, {
        relative_directory: directory,
        depth: 3,
        max_entries: 200,
      }),
    );
    if (completed?.result?.kind === "workspace_list_v1") {
      setEntries(completed.result.entries);
    }
  }

  async function runRead() {
    const completed = await executeAction("Read", () =>
      readWorkspaceText(workspaceId, {
        relative_path: readPath,
        max_bytes: 32768,
      }),
    );
    if (completed?.result?.kind === "workspace_read_text_v1") {
      setReadContent(completed.result.content);
      setCurrentHash(completed.result.sha256);
      setExpectedHash(completed.result.sha256);
      setWritePath(completed.result.relative_path);
    }
  }

  async function runWrite() {
    const input =
      writeMode === "create"
        ? {
            mode: "create" as const,
            relative_path: writePath,
            content: writeContent,
            expected_absent: true as const,
          }
        : {
            mode: "replace" as const,
            relative_path: writePath,
            content: writeContent,
            expected_sha256: expectedHash,
          };
    const completed = await executeAction(
      writeMode === "create" ? "Create text" : "Replace text",
      () => writeWorkspaceText(workspaceId, input),
    );
    if (completed?.result?.kind === "workspace_write_text_v1") {
      setCurrentHash(completed.result.sha256);
      setExpectedHash(completed.result.sha256);
    }
  }

  function selectWriteMode(mode: "create" | "replace") {
    setWriteMode(mode);
    if (mode === "create") {
      setWritePath("sandbox/create-here/new-file.txt");
      setExpectedHash("");
    } else {
      setWritePath(readPath);
      setExpectedHash(currentHash);
    }
  }

  const actionable =
    workspace &&
    ["ready", "active", "sealed", "rolled_back"].includes(workspace.state);
  const writable =
    workspace && ["ready", "active"].includes(workspace.state) && !busy;
  const discardable =
    workspace &&
    ["sealed", "rolled_back", "failed", "expired"].includes(workspace.state);

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <Link
        href="/workspaces"
        className="inline-flex rounded-lg px-2 py-1 text-sm font-semibold text-blue-700 outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
      >
        ← Workspaces
      </Link>
      {state === "loading" ? (
        <p
          className="mt-6 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600"
          role="status"
        >
          正在加载 Workspace、Timeline 与 Checkpoints…
        </p>
      ) : null}
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
      {notice ? (
        <p
          className="mt-6 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900"
          role="status"
        >
          {notice}
        </p>
      ) : null}

      {workspace ? (
        <>
          <header className="mt-6 border-b border-slate-200 pb-8">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold tracking-widest text-blue-700 uppercase">
                  Runner-owned isolated workspace
                </p>
                <h1 className="mt-3 text-2xl font-semibold tracking-tight break-words text-slate-950 sm:text-4xl">
                  {workspace.repository_display_name}
                </h1>
                <p className="mt-2 font-mono text-xs break-all text-slate-500">
                  {workspace.id}
                </p>
              </div>
              <StatusPill tone={tone(workspace.state)}>
                {workspace.state}
              </StatusPill>
            </div>
            {workspace.state === "discarded" ? (
              <p className="mt-5 rounded-xl border border-slate-300 bg-slate-100 p-4 text-sm font-semibold text-slate-800">
                Workspace 已销毁。Runner 路径已清理；只保留 Control Plane
                证据与事件。
              </p>
            ) : null}
            {workspace.state === "expired" ? (
              <p className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                Workspace 已过期，只允许受控 Discard。
              </p>
            ) : null}
            <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <dt className="font-semibold text-slate-500">Runner</dt>
                <dd className="mt-1">{workspace.runner_display_name}</dd>
              </div>
              <div>
                <dt className="font-semibold text-slate-500">Grant</dt>
                <dd className="mt-1 font-mono text-xs break-all">
                  {workspace.grant_id}
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-slate-500">
                  Workspace fingerprint
                </dt>
                <dd className="mt-1 font-mono text-xs break-all">
                  {workspace.workspace_fingerprint ?? "preparing"}
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
              <div>
                <dt className="font-semibold text-slate-500">Budget usage</dt>
                <dd className="mt-1">
                  {workspace.changed_file_count}/{workspace.max_files_changed}{" "}
                  files · {workspace.total_written_bytes}/
                  {workspace.max_total_write_bytes} bytes
                </dd>
              </div>
            </dl>
          </header>

          <section
            className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
            aria-labelledby="typed-tools-heading"
          >
            <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
              Fixture-only manual controls
            </p>
            <h2
              id="typed-tools-heading"
              className="mt-1 text-xl font-semibold text-slate-950"
            >
              Typed Tool Console
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              固定能力，无自由 Shell。所有路径都是相对 POSIX path，并再次受
              Execution Grant、Runner FD walker 与 lease fencing 校验。
            </p>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <fieldset className="min-w-0 rounded-xl border border-slate-200 p-4">
                <legend className="px-2 font-semibold text-slate-900">
                  List / Read
                </legend>
                <label className="block text-sm font-semibold text-slate-700">
                  Relative directory
                  <input
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                    value={directory}
                    onChange={(event) =>
                      setDirectory(event.currentTarget.value)
                    }
                  />
                </label>
                <button
                  type="button"
                  className="mt-3 rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 ring-1 ring-blue-300 outline-none focus-visible:ring-2 focus-visible:ring-blue-700 disabled:opacity-50"
                  disabled={!actionable || Boolean(busy)}
                  onClick={() => void runList()}
                >
                  List
                </button>
                <label className="mt-5 block text-sm font-semibold text-slate-700">
                  Relative text path
                  <input
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                    value={readPath}
                    onChange={(event) => setReadPath(event.currentTarget.value)}
                  />
                </label>
                <button
                  type="button"
                  className="mt-3 rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 ring-1 ring-blue-300 outline-none focus-visible:ring-2 focus-visible:ring-blue-700 disabled:opacity-50"
                  disabled={!actionable || Boolean(busy)}
                  onClick={() => void runRead()}
                >
                  Read text
                </button>
              </fieldset>

              <fieldset className="min-w-0 rounded-xl border border-slate-200 p-4">
                <legend className="px-2 font-semibold text-slate-900">
                  Create / Replace text
                </legend>
                <div className="flex gap-4">
                  {(["replace", "create"] as const).map((mode) => (
                    <label
                      key={mode}
                      className="flex items-center gap-2 text-sm"
                    >
                      <input
                        type="radio"
                        name="write-mode"
                        checked={writeMode === mode}
                        onChange={() => selectWriteMode(mode)}
                      />
                      {mode}
                    </label>
                  ))}
                </div>
                <label className="mt-4 block text-sm font-semibold text-slate-700">
                  Relative path
                  <input
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                    value={writePath}
                    onChange={(event) =>
                      setWritePath(event.currentTarget.value)
                    }
                  />
                </label>
                {writeMode === "replace" ? (
                  <label className="mt-4 block text-sm font-semibold text-slate-700">
                    Expected SHA-256
                    <input
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                      value={expectedHash}
                      onChange={(event) =>
                        setExpectedHash(event.currentTarget.value)
                      }
                    />
                  </label>
                ) : null}
                <label className="mt-4 block text-sm font-semibold text-slate-700">
                  UTF-8 content
                  <textarea
                    className="mt-1 min-h-28 w-full resize-y rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                    value={writeContent}
                    onChange={(event) =>
                      setWriteContent(event.currentTarget.value)
                    }
                  />
                </label>
                <dl
                  className="mt-4 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 rounded-lg bg-slate-50 p-3 text-xs"
                  aria-label="Write preflight"
                >
                  <dt className="font-semibold">Relative path</dt>
                  <dd className="font-mono break-all">{writePath}</dd>
                  <dt className="font-semibold">Operation</dt>
                  <dd>{writeMode}</dd>
                  <dt className="font-semibold">Current hash</dt>
                  <dd className="font-mono break-all">
                    {currentHash || "not read"}
                  </dd>
                  <dt className="font-semibold">Expected hash</dt>
                  <dd className="font-mono break-all">
                    {writeMode === "create"
                      ? "expected_absent=true"
                      : expectedHash || "required"}
                  </dd>
                  <dt className="font-semibold">New byte size</dt>
                  <dd>{newByteSize}</dd>
                  <dt className="font-semibold">Remaining budget</dt>
                  <dd>{remainingBytes} bytes</dd>
                </dl>
                <button
                  type="button"
                  className="mt-4 w-full rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2 disabled:opacity-50"
                  disabled={
                    !writable ||
                    !writePath ||
                    !writeContent ||
                    newByteSize > remainingBytes ||
                    newByteSize > workspace.max_single_file_bytes ||
                    (writeMode === "replace" && expectedHash.length !== 64)
                  }
                  onClick={() => void runWrite()}
                >
                  {busy ||
                    (writeMode === "create" ? "Create text" : "Replace text")}
                </button>
              </fieldset>
            </div>

            <div className="mt-6 flex flex-wrap gap-3 border-t border-slate-200 pt-5">
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 ring-1 ring-blue-300 outline-none focus-visible:ring-2 focus-visible:ring-blue-700 disabled:opacity-50"
                disabled={!actionable || Boolean(busy)}
                onClick={() =>
                  void executeAction("Status", () =>
                    getWorkspaceStatus(workspaceId),
                  )
                }
              >
                Status
              </button>
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 ring-1 ring-blue-300 outline-none focus-visible:ring-2 focus-visible:ring-blue-700 disabled:opacity-50"
                disabled={
                  !workspace ||
                  !["ready", "active", "sealed"].includes(workspace.state) ||
                  Boolean(busy)
                }
                onClick={() =>
                  void executeAction("Diff + Seal", () =>
                    getWorkspaceDiff(workspaceId),
                  )
                }
              >
                Diff + Seal
              </button>
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-sm font-semibold text-amber-800 ring-1 ring-amber-300 outline-none focus-visible:ring-2 focus-visible:ring-amber-700 disabled:opacity-50"
                disabled={
                  !workspace ||
                  !["ready", "active", "sealed"].includes(workspace.state) ||
                  Boolean(busy)
                }
                onClick={() =>
                  void executeAction("Rollback", () =>
                    rollbackWorkspace(workspaceId),
                  )
                }
              >
                Rollback to initial
              </button>
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-sm font-semibold text-red-700 ring-1 ring-red-300 outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-50"
                disabled={!discardable || Boolean(busy)}
                onClick={() =>
                  void executeAction("Discard", () =>
                    discardWorkspace(workspaceId),
                  )
                }
              >
                Discard
              </button>
            </div>
          </section>

          <div className="mt-8 grid items-start gap-6 lg:grid-cols-2">
            <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-semibold text-slate-950">
                Tool output
              </h2>
              {entries.length > 0 ? (
                <ul className="mt-4 divide-y divide-slate-100 text-sm">
                  {entries.map((entry) => (
                    <li
                      key={entry.relative_path}
                      className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 py-2"
                    >
                      <span className="font-mono break-all">
                        {entry.relative_path}
                      </span>
                      <span className="text-slate-500">
                        {entry.entry_type} · {entry.size} B
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-slate-600">List 结果为空。</p>
              )}
              {readContent ? (
                <div className="mt-5">
                  <p className="text-xs font-semibold text-slate-500">
                    Read SHA-256
                  </p>
                  <p className="mt-1 font-mono text-xs break-all">
                    {currentHash}
                  </p>
                  <pre className="mt-3 max-h-64 overflow-auto rounded-lg bg-slate-950 p-4 text-xs break-words whitespace-pre-wrap text-slate-100">
                    {readContent}
                  </pre>
                </div>
              ) : null}
              {lastJob ? (
                <p className="mt-4 text-xs text-slate-500">
                  Last Job {lastJob.kind} · {lastJob.state} ·{" "}
                  {lastJob.id.slice(0, 8)}
                </p>
              ) : null}
            </section>

            <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-semibold text-slate-950">
                Bounded Diff & Checkpoints
              </h2>
              <p className="mt-2 text-sm font-semibold text-emerald-800">
                No source repository write · no Git delivery
              </p>
              {checkpoints.length === 0 ? (
                <p className="mt-4 text-sm text-slate-600">
                  尚无 Checkpoint；成功 write 或 diff 后自动生成。
                </p>
              ) : (
                <ol className="mt-4 space-y-5">
                  {checkpoints.map((checkpoint) => (
                    <li
                      key={checkpoint.id}
                      className="min-w-0 rounded-xl border border-slate-200 p-4"
                    >
                      <p className="font-semibold text-slate-900">
                        Checkpoint #{checkpoint.sequence}
                      </p>
                      <p className="mt-2 font-mono text-xs break-all text-slate-500">
                        diff {checkpoint.diff_hash}
                      </p>
                      <p className="mt-2 text-xs text-slate-600">
                        {checkpoint.changed_paths.join(", ") || "clean"} ·{" "}
                        {checkpoint.total_diff_bytes} bytes
                      </p>
                      <pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs break-words whitespace-pre-wrap text-slate-100">
                        {checkpoint.diff_artifact || "(empty diff)"}
                      </pre>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>

          <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-950">
              Workspace Timeline
            </h2>
            {events.length === 0 ? (
              <p className="mt-3 text-sm text-slate-600">暂无事件。</p>
            ) : (
              <ol className="mt-5 space-y-4">
                {events.map((event) => (
                  <li
                    key={event.id}
                    className="grid gap-1 border-l-2 border-blue-200 pl-4 text-sm sm:grid-cols-[10rem_minmax(0,1fr)]"
                  >
                    <time className="text-xs text-slate-500">
                      {formatTimestamp(event.created_at)}
                    </time>
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-900">
                        {event.sequence}. {event.event_type}
                      </p>
                      <p className="mt-1 font-mono text-xs break-all text-slate-500">
                        {JSON.stringify(event.metadata)}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </>
      ) : null}
    </main>
  );
}
