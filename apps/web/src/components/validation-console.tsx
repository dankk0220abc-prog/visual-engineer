"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  cancelValidationRun,
  createExecutionGrant,
  createValidationRun,
  decideExecutionGrant,
  listExecutionGrants,
  listValidationProfiles,
  listValidationRuns,
  listWorkspaceCheckpoints,
  listWorkspaces,
  type ExecutionGrant,
  type ValidationProfile,
  type ValidationRun,
  type Workspace,
  type WorkspaceCheckpoint,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";

import { StatusPill } from "./status-pill";

type Candidate = {
  workspace: Workspace;
  checkpoint: WorkspaceCheckpoint;
  implementationGrant: ExecutionGrant;
};

const activeStates = new Set([
  "requested",
  "queued",
  "claimed",
  "running",
  "cancel_requested",
]);

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.code}: ${error.message}${
      error.requestId ? `（请求 ID：${error.requestId}）` : ""
    }`;
  }
  return "出现未预期的错误。";
}

function runTone(
  state: ValidationRun["state"],
): "neutral" | "positive" | "negative" | "pending" {
  if (state === "succeeded") return "positive";
  if (
    state === "failed" ||
    state === "timed_out" ||
    state === "recovery_required"
  ) {
    return "negative";
  }
  if (activeStates.has(state)) return "pending";
  return "neutral";
}

function grantTone(
  state: ExecutionGrant["status"],
): "neutral" | "positive" | "negative" | "pending" {
  if (state === "approved") return "positive";
  if (state === "pending" || state === "revoke_requested") return "pending";
  if (state === "rejected" || state === "revoked") return "negative";
  return "neutral";
}

export function ValidationConsole() {
  const [profiles, setProfiles] = useState<ValidationProfile[]>([]);
  const [runs, setRuns] = useState<ValidationRun[]>([]);
  const [grants, setGrants] = useState<ExecutionGrant[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [rejectReasons, setRejectReasons] = useState<Record<string, string>>(
    {},
  );

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [nextProfiles, nextRuns, nextGrants, workspaces] =
        await Promise.all([
          listValidationProfiles(),
          listValidationRuns(),
          listExecutionGrants(),
          listWorkspaces(),
        ]);
      const eligibleWorkspaces = workspaces.filter(
        (workspace) =>
          workspace.current_tree_hash &&
          ["ready", "active", "sealed", "rolled_back"].includes(
            workspace.state,
          ),
      );
      const checkpointLists = await Promise.all(
        eligibleWorkspaces.map((workspace) =>
          listWorkspaceCheckpoints(workspace.id),
        ),
      );
      const nextCandidates = eligibleWorkspaces.flatMap(
        (workspace, index): Candidate[] => {
          const implementationGrant = nextGrants.find(
            (grant) => grant.id === workspace.grant_id,
          );
          if (!implementationGrant) return [];
          return checkpointLists[index]
            .filter(
              (checkpoint) =>
                checkpoint.tree_fingerprint === workspace.current_tree_hash,
            )
            .map((checkpoint) => ({
              workspace,
              checkpoint,
              implementationGrant,
            }));
        },
      );
      setProfiles(nextProfiles);
      setRuns(nextRuns);
      setGrants(nextGrants);
      setCandidates(nextCandidates);
      setSelectedCheckpoint((current) =>
        nextCandidates.some((candidate) => candidate.checkpoint.id === current)
          ? current
          : (nextCandidates[0]?.checkpoint.id ?? ""),
      );
      setState("ready");
    } catch (reason) {
      setError(errorMessage(reason));
      setState("error");
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  useEffect(() => {
    if (!runs.some((run) => activeStates.has(run.state))) return;
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => window.clearInterval(timer);
  }, [refresh, runs]);

  const selectedCandidate = useMemo(
    () =>
      candidates.find(
        (candidate) => candidate.checkpoint.id === selectedCheckpoint,
      ) ?? null,
    [candidates, selectedCheckpoint],
  );
  const validationGrants = useMemo(
    () => grants.filter((grant) => grant.validation_checkpoint_id !== null),
    [grants],
  );
  const profile = profiles[0] ?? null;

  async function requestGrant() {
    if (!selectedCandidate || !profile) return;
    setBusy("create-grant");
    setError("");
    try {
      await createExecutionGrant({
        plan_id: selectedCandidate.implementationGrant.plan_id,
        repository_handle_id:
          selectedCandidate.implementationGrant.repository_handle_id,
        validation_checkpoint_id: selectedCandidate.checkpoint.id,
        validation_profile_id: profile.profile_id,
      });
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function decideGrant(
    grant: ExecutionGrant,
    decision: "approve" | "reject",
  ) {
    setBusy(`${decision}-${grant.id}`);
    setError("");
    try {
      await decideExecutionGrant(grant.id, {
        decision,
        reason:
          decision === "approve"
            ? "Reviewed exact Checkpoint, fixed Profile, and validation-only budgets."
            : rejectReasons[grant.id],
      });
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function startValidation(grant: ExecutionGrant) {
    if (!profile) return;
    setBusy(`run-${grant.id}`);
    setError("");
    try {
      await createValidationRun(
        {
          execution_grant_id: grant.id,
          profile_id: profile.profile_id,
        },
        `validation-${grant.id}-${crypto.randomUUID()}`,
      );
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function cancel(run: ValidationRun) {
    setBusy(`cancel-${run.id}`);
    setError("");
    try {
      await cancelValidationRun(run.id);
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="border-b border-slate-200 pb-8">
        <p className="text-sm font-semibold tracking-widest text-blue-700 uppercase">
          Governed Validation Execution
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          Validation Runs
        </h1>
        <p className="mt-3 max-w-4xl text-base leading-7 font-semibold text-slate-800">
          对精确 Workspace Checkpoint 运行一个系统所有、不可参数化的验证
          Profile；每次执行仍需独立的 validation-only Execution Grant。
        </p>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
          本页不接受命令、argv、cwd、环境变量、依赖安装或 Provider 配置。网络与
          Shell 均保持关闭。
        </p>
      </header>

      {error ? (
        <div
          className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900"
          role="alert"
        >
          {error}
          {state === "error" ? (
            <button
              type="button"
              className="ml-3 font-semibold underline"
              onClick={() => void refresh()}
            >
              重试
            </button>
          ) : null}
        </div>
      ) : null}

      {state === "loading" ? (
        <p className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">
          正在加载 Validation 权限与证据…
        </p>
      ) : null}

      {state === "ready" ? (
        <>
          <section className="mt-8 grid gap-5 lg:grid-cols-2">
            <div className="rounded-2xl border border-blue-200 bg-blue-50/60 p-5 sm:p-6">
              <h2 className="text-xl font-semibold text-slate-950">
                1. 申请 validation-only Grant
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                只有与当前 Workspace tree fingerprint 精确一致的 Checkpoint
                可选；创建后必须显式 Approve 才能运行。
              </p>
              {candidates.length === 0 ? (
                <p className="mt-4 rounded-xl border border-dashed border-blue-300 p-4 text-sm text-slate-700">
                  当前没有可验证的精确 Checkpoint。先在 Workspace 中生成一次
                  status、diff 或 write Checkpoint。
                </p>
              ) : (
                <div className="mt-4 space-y-3">
                  <label className="block text-sm font-semibold text-slate-800">
                    Exact Workspace Checkpoint
                    <select
                      className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-200"
                      value={selectedCheckpoint}
                      onChange={(event) =>
                        setSelectedCheckpoint(event.currentTarget.value)
                      }
                    >
                      {candidates.map((candidate) => (
                        <option
                          key={candidate.checkpoint.id}
                          value={candidate.checkpoint.id}
                        >
                          {candidate.workspace.repository_display_name} · W
                          {candidate.workspace.id.slice(0, 8)} · C
                          {candidate.checkpoint.sequence}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-blue-800 focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2 disabled:opacity-50"
                    disabled={
                      !selectedCandidate || !profile || busy === "create-grant"
                    }
                    onClick={() => void requestGrant()}
                  >
                    {busy === "create-grant"
                      ? "创建中…"
                      : "创建 pending Validation Grant"}
                  </button>
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <h2 className="text-xl font-semibold text-slate-950">
                固定 Profile 与上限
              </h2>
              {profile ? (
                <>
                  <p className="mt-3 font-semibold text-slate-900">
                    {profile.display_name}
                  </p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    {profile.description}
                  </p>
                  <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="font-semibold text-slate-500">Profile</dt>
                      <dd className="font-mono text-xs">
                        {profile.profile_id}:v{profile.version}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        Fixed argv
                      </dt>
                      <dd className="font-mono text-xs break-all">
                        {profile.safe_argv.join(" ")}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">Budgets</dt>
                      <dd>
                        {profile.timeout_seconds}s · {profile.max_output_bytes}{" "}
                        output bytes · {profile.max_artifact_count} artifacts
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        Explicit denials
                      </dt>
                      <dd>
                        network {profile.network_policy} · Shell{" "}
                        {String(profile.shell_access)} · user command{" "}
                        {String(profile.user_command_input)}
                      </dd>
                    </div>
                  </dl>
                </>
              ) : (
                <p className="mt-3 text-sm text-slate-600">
                  没有可用的系统 Profile。
                </p>
              )}
            </div>
          </section>

          <section className="mt-10">
            <h2 className="text-2xl font-semibold text-slate-950">
              2. 独立审批与启动
            </h2>
            {validationGrants.length === 0 ? (
              <p className="mt-4 rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-600">
                尚无 Validation Grant。
              </p>
            ) : (
              <ul className="mt-5 grid gap-5 lg:grid-cols-2">
                {validationGrants.map((grant) => (
                  <li
                    key={grant.id}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-mono text-xs break-all text-slate-500">
                          {grant.id}
                        </p>
                        <p className="mt-2 text-sm font-semibold text-slate-900">
                          {grant.allowed_validation_profiles.join(", ")}
                        </p>
                      </div>
                      <StatusPill tone={grantTone(grant.status)}>
                        {grant.status}
                      </StatusPill>
                    </div>
                    <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                      <div>
                        <dt className="font-semibold text-slate-500">
                          Workspace / Checkpoint
                        </dt>
                        <dd className="mt-1 font-mono text-xs break-all">
                          {grant.validation_workspace_id} /{" "}
                          {grant.validation_checkpoint_id}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-semibold text-slate-500">Limits</dt>
                        <dd className="mt-1">
                          {grant.max_validation_runs} runs ·{" "}
                          {grant.validation_timeout_seconds}s ·{" "}
                          {grant.validation_output_bytes} bytes
                        </dd>
                      </div>
                    </dl>
                    {grant.status === "pending" ? (
                      <div className="mt-5 space-y-3 border-t border-slate-200 pt-4">
                        <button
                          type="button"
                          className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 disabled:opacity-50"
                          disabled={Boolean(busy)}
                          onClick={() => void decideGrant(grant, "approve")}
                        >
                          {busy === `approve-${grant.id}`
                            ? "批准中…"
                            : "Approve exact Validation Grant"}
                        </button>
                        <div className="flex gap-2">
                          <label className="min-w-0 flex-1 text-sm font-semibold text-slate-700">
                            Reject reason
                            <input
                              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-red-600 focus:ring-2 focus:ring-red-100"
                              value={rejectReasons[grant.id] ?? ""}
                              onChange={(event) =>
                                setRejectReasons((current) => ({
                                  ...current,
                                  [grant.id]: event.currentTarget.value,
                                }))
                              }
                            />
                          </label>
                          <button
                            type="button"
                            className="self-end rounded-lg px-4 py-2 text-sm font-semibold text-red-700 ring-1 ring-red-300 disabled:opacity-50"
                            disabled={
                              Boolean(busy) ||
                              !(rejectReasons[grant.id] ?? "").trim()
                            }
                            onClick={() => void decideGrant(grant, "reject")}
                          >
                            Reject
                          </button>
                        </div>
                      </div>
                    ) : null}
                    {grant.status === "approved" ? (
                      <button
                        type="button"
                        className="mt-5 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-700 disabled:opacity-50"
                        disabled={Boolean(busy)}
                        onClick={() => void startValidation(grant)}
                      >
                        {busy === `run-${grant.id}`
                          ? "排队中…"
                          : "Run fixed Profile"}
                      </button>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="mt-10">
            <h2 className="text-2xl font-semibold text-slate-950">
              3. 状态与结构化证据
            </h2>
            {runs.length === 0 ? (
              <p className="mt-4 rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-600">
                尚无 Validation Run。
              </p>
            ) : (
              <ul className="mt-5 space-y-5">
                {runs.map((run) => (
                  <li
                    key={run.id}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
                          {run.profile_id}:v{run.profile_version}
                        </p>
                        <h3 className="mt-1 font-mono text-sm break-all text-slate-950">
                          {run.id}
                        </h3>
                      </div>
                      <StatusPill tone={runTone(run.state)}>
                        {run.state}
                      </StatusPill>
                    </div>
                    <dl className="mt-4 grid gap-3 text-sm md:grid-cols-3">
                      <div>
                        <dt className="font-semibold text-slate-500">
                          Checkpoint fingerprint
                        </dt>
                        <dd className="mt-1 font-mono text-xs break-all">
                          {run.checkpoint_fingerprint}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-semibold text-slate-500">
                          Step / exit
                        </dt>
                        <dd className="mt-1">
                          {run.step.step_id} · {run.step.state} · exit{" "}
                          {run.step.exit_code ?? "—"}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-semibold text-slate-500">Timing</dt>
                        <dd className="mt-1">
                          requested {formatTimestamp(run.requested_at)}
                          {run.completed_at
                            ? ` · completed ${formatTimestamp(run.completed_at)}`
                            : ""}
                        </dd>
                      </div>
                    </dl>
                    {run.error_code ? (
                      <p
                        className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-900"
                        role="status"
                      >
                        {run.error_code}: {run.error_message}
                      </p>
                    ) : null}
                    {run.evidence ? (
                      <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                        <dl className="grid gap-3 text-sm md:grid-cols-3">
                          <div>
                            <dt className="font-semibold text-slate-500">
                              Isolation
                            </dt>
                            <dd>
                              network {String(run.evidence.network_isolated)} ·
                              filesystem{" "}
                              {String(run.evidence.filesystem_isolated)} ·
                              cleaned {String(run.evidence.sandbox_cleaned)}
                            </dd>
                          </div>
                          <div>
                            <dt className="font-semibold text-slate-500">
                              Bounded result
                            </dt>
                            <dd>
                              {run.evidence.duration_ms}ms · exit{" "}
                              {run.evidence.exit_code} · redactions{" "}
                              {run.evidence.redaction_count}
                            </dd>
                          </div>
                          <div>
                            <dt className="font-semibold text-slate-500">
                              Fixed argv
                            </dt>
                            <dd className="font-mono text-xs break-all">
                              {run.evidence.fixed_argv.join(" ")}
                            </dd>
                          </div>
                        </dl>
                        <div className="mt-4 grid gap-3 lg:grid-cols-2">
                          <div>
                            <h4 className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
                              stdout
                            </h4>
                            <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-slate-950 p-3 text-xs whitespace-pre-wrap text-slate-100">
                              {run.evidence.stdout || "(empty)"}
                            </pre>
                          </div>
                          <div>
                            <h4 className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
                              stderr
                            </h4>
                            <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-slate-950 p-3 text-xs whitespace-pre-wrap text-slate-100">
                              {run.evidence.stderr || "(empty)"}
                            </pre>
                          </div>
                        </div>
                      </div>
                    ) : null}
                    <div className="mt-5 flex flex-wrap gap-3">
                      <Link
                        href={`/workspaces/${run.workspace_id}`}
                        className="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 ring-1 ring-blue-300"
                      >
                        Workspace
                      </Link>
                      {run.runner_job_id ? (
                        <Link
                          href={`/runners/jobs/${run.runner_job_id}`}
                          className="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 ring-1 ring-blue-300"
                        >
                          Runner Job
                        </Link>
                      ) : null}
                      {activeStates.has(run.state) &&
                      run.state !== "cancel_requested" ? (
                        <button
                          type="button"
                          className="rounded-lg px-3 py-2 text-sm font-semibold text-red-700 ring-1 ring-red-300 disabled:opacity-50"
                          disabled={Boolean(busy)}
                          onClick={() => void cancel(run)}
                        >
                          {busy === `cancel-${run.id}`
                            ? "取消中…"
                            : "Cancel Validation"}
                        </button>
                      ) : null}
                    </div>
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
