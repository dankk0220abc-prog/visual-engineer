"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  cancelValidationSuiteRun,
  cancelValidationRun,
  createExecutionGrant,
  createValidationSuiteRun,
  createValidationRun,
  decideExecutionGrant,
  listExecutionGrants,
  listValidationProfiles,
  listValidationRuns,
  listValidationSuiteRuns,
  listValidationSuites,
  listWorkspaceCheckpoints,
  listWorkspaces,
  retryValidationSuiteRun,
  type ExecutionGrant,
  type ValidationProfile,
  type ValidationRun,
  type ValidationSuite,
  type ValidationSuiteRun,
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
const activeSuiteStates = new Set([
  "requested",
  "queued",
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
  state: string,
): "neutral" | "positive" | "negative" | "pending" {
  if (state === "succeeded") return "positive";
  if (
    state === "failed" ||
    state === "timed_out" ||
    state === "recovery_required"
  ) {
    return "negative";
  }
  if (activeStates.has(state as ValidationRun["state"])) return "pending";
  if (state === "pending") return "pending";
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
  const [suites, setSuites] = useState<ValidationSuite[]>([]);
  const [suiteRuns, setSuiteRuns] = useState<ValidationSuiteRun[]>([]);
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
      const [
        nextProfiles,
        nextRuns,
        nextSuites,
        nextSuiteRuns,
        nextGrants,
        workspaces,
      ] = await Promise.all([
        listValidationProfiles(),
        listValidationRuns(),
        listValidationSuites(),
        listValidationSuiteRuns(),
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
      setSuites(nextSuites);
      setSuiteRuns(nextSuiteRuns);
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
    if (
      !runs.some((run) => activeStates.has(run.state)) &&
      !suiteRuns.some((run) => activeSuiteStates.has(run.state))
    )
      return;
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => window.clearInterval(timer);
  }, [refresh, runs, suiteRuns]);

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
  const suite = suites[0] ?? null;

  async function requestGrant() {
    if (!selectedCandidate || !suite) return;
    setBusy("create-grant");
    setError("");
    try {
      await createExecutionGrant({
        plan_id: selectedCandidate.implementationGrant.plan_id,
        repository_handle_id:
          selectedCandidate.implementationGrant.repository_handle_id,
        validation_checkpoint_id: selectedCandidate.checkpoint.id,
        validation_suite_id: suite.suite_id,
        validation_suite_version: suite.suite_version,
      });
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function startSuite(grant: ExecutionGrant) {
    if (!suite) return;
    setBusy(`suite-${grant.id}`);
    setError("");
    try {
      await createValidationSuiteRun(
        {
          execution_grant_id: grant.id,
          suite_id: suite.suite_id,
          suite_version: suite.suite_version,
        },
        `validation-suite-${grant.id}-${crypto.randomUUID()}`,
      );
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function cancelSuite(run: ValidationSuiteRun) {
    setBusy(`cancel-suite-${run.id}`);
    setError("");
    try {
      await cancelValidationSuiteRun(run.id);
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function retrySuite(run: ValidationSuiteRun, grant: ExecutionGrant) {
    setBusy(`retry-suite-${run.id}`);
    setError("");
    try {
      await retryValidationSuiteRun(
        run.id,
        { execution_grant_id: grant.id },
        `validation-suite-retry-${run.id}-${crypto.randomUUID()}`,
      );
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function requestRetryGrant(run: ValidationSuiteRun) {
    const candidate = candidates.find(
      (item) => item.checkpoint.id === run.checkpoint_id,
    );
    if (!candidate || !suite) return;
    setBusy(`retry-grant-${run.id}`);
    setError("");
    try {
      await createExecutionGrant({
        plan_id: candidate.implementationGrant.plan_id,
        repository_handle_id:
          candidate.implementationGrant.repository_handle_id,
        validation_checkpoint_id: run.checkpoint_id,
        validation_suite_id: suite.suite_id,
        validation_suite_version: suite.suite_version,
        validation_suite_retry_of_run_id: run.id,
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
            ? grant.allowed_validation_suites.length
              ? "Reviewed exact Checkpoint, fixed Suite, and validation-only budgets."
              : "Reviewed exact Checkpoint, fixed Profile, and validation-only budgets."
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
          对精确 Workspace Checkpoint 串行运行系统所有、不可参数化的多步骤
          Validation Suite；每个实际步骤都有独立 Runner Attempt、Lease 和
          Evidence。
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
                      !selectedCandidate || !suite || busy === "create-grant"
                    }
                    onClick={() => void requestGrant()}
                  >
                    {busy === "create-grant"
                      ? "创建中…"
                      : "创建 pending Suite Grant"}
                  </button>
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <h2 className="text-xl font-semibold text-slate-950">
                固定 Suite、步骤与上限
              </h2>
              {suite ? (
                <>
                  <p className="mt-3 font-semibold text-slate-900">
                    {suite.name}
                  </p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    {suite.purpose}
                  </p>
                  <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="font-semibold text-slate-500">Suite</dt>
                      <dd className="font-mono text-xs">
                        {suite.suite_id}:v{suite.suite_version}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        Ordered steps
                      </dt>
                      <dd>
                        {suite.steps.length} · {suite.failure_policy}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">Budgets</dt>
                      <dd>
                        {suite.total_timeout_seconds}s total ·{" "}
                        {suite.total_output_bytes} output bytes ·{" "}
                        {suite.max_attempts} attempts
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        Explicit denials
                      </dt>
                      <dd>
                        network {suite.network_policy} · Shell{" "}
                        {String(suite.shell_access)} · user command{" "}
                        {String(suite.user_command_input)} · artifacts{" "}
                        {String(suite.artifact_content_transfer)}
                      </dd>
                    </div>
                  </dl>
                  <ol className="mt-4 space-y-2">
                    {suite.steps.map((step) => (
                      <li
                        key={step.step_id}
                        className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm"
                      >
                        <span className="font-semibold">
                          {step.sequence}. {step.step_id}
                        </span>
                        <span className="mt-1 block font-mono text-xs text-slate-600">
                          {step.profile_id}:v{step.profile_version} ·{" "}
                          {step.timeout_seconds}s · {step.max_output_bytes}{" "}
                          bytes
                        </span>
                      </li>
                    ))}
                  </ol>
                </>
              ) : (
                <p className="mt-3 text-sm text-slate-600">
                  没有可用的系统 Suite。
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
                          {grant.allowed_validation_suites.length
                            ? grant.allowed_validation_suites.join(", ")
                            : grant.allowed_validation_profiles.join(", ")}
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
                      grant.allowed_validation_suites.length ? (
                        grant.validation_suite_attempt_number === 1 ? (
                          <button
                            type="button"
                            className="mt-5 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-700 disabled:opacity-50"
                            disabled={Boolean(busy)}
                            onClick={() => void startSuite(grant)}
                          >
                            {busy === `suite-${grant.id}`
                              ? "排队中…"
                              : "Run fixed Suite"}
                          </button>
                        ) : (
                          <p className="mt-5 text-xs text-slate-600">
                            此 Grant 仅绑定 Suite retry source{" "}
                            {grant.validation_suite_retry_of_run_id}。
                          </p>
                        )
                      ) : (
                        <button
                          type="button"
                          className="mt-5 rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-slate-700 disabled:opacity-50"
                          disabled={Boolean(busy)}
                          onClick={() => void startValidation(grant)}
                        >
                          {busy === `run-${grant.id}`
                            ? "排队中…"
                            : "Run sealed first-slice Profile"}
                        </button>
                      )
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="mt-10">
            <h2 className="text-2xl font-semibold text-slate-950">
              3. Suite 时间线与聚合结果
            </h2>
            {suiteRuns.length === 0 ? (
              <p className="mt-4 rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-600">
                尚无 Validation Suite Run。
              </p>
            ) : (
              <ul className="mt-5 space-y-5">
                {suiteRuns.map((run) => {
                  const retryGrant = validationGrants.find(
                    (grant) =>
                      grant.id !== run.execution_grant_id &&
                      grant.status === "approved" &&
                      grant.validation_checkpoint_id === run.checkpoint_id &&
                      grant.validation_suite_retry_of_run_id === run.id &&
                      grant.validation_suite_attempt_number ===
                        run.attempt_number + 1 &&
                      grant.allowed_validation_suites.includes(
                        `${run.suite_id}:v${run.suite_version}`,
                      ),
                  );
                  const retryable = [
                    "failed",
                    "timed_out",
                    "cancelled",
                    "recovery_required",
                  ].includes(run.state);
                  return (
                    <li
                      key={run.id}
                      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
                            {run.suite_id}:v{run.suite_version} · attempt{" "}
                            {run.attempt_number}/{run.max_attempts}
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
                            Authority
                          </dt>
                          <dd className="mt-1 font-mono text-xs break-all">
                            {run.checkpoint_fingerprint}
                          </dd>
                        </div>
                        <div>
                          <dt className="font-semibold text-slate-500">
                            Aggregate budget
                          </dt>
                          <dd className="mt-1">
                            {run.combined_output_bytes}/{run.total_output_bytes}{" "}
                            bytes · {run.total_timeout_seconds}s
                          </dd>
                        </div>
                        <div>
                          <dt className="font-semibold text-slate-500">
                            Progress
                          </dt>
                          <dd className="mt-1">
                            {run.completed_step_count}/{run.step_count} terminal
                            steps
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
                      <ol
                        className="mt-5 space-y-3"
                        aria-label="Validation Suite step timeline"
                      >
                        {run.steps.map((step) => (
                          <li
                            key={step.id}
                            className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div>
                                <p className="font-semibold text-slate-900">
                                  {step.sequence}. {step.step_id}
                                </p>
                                <p className="mt-1 font-mono text-xs text-slate-600">
                                  {step.profile_id}:v{step.profile_version}
                                  {step.reused_from_step_run_id
                                    ? " · reused successful Evidence"
                                    : ""}
                                </p>
                              </div>
                              <StatusPill tone={runTone(step.state)}>
                                {step.state}
                              </StatusPill>
                            </div>
                            <p className="mt-2 text-sm text-slate-700">
                              duration {step.duration_ms ?? "—"}ms · exit{" "}
                              {step.exit_code ?? "—"} · output{" "}
                              {step.output_bytes}/{step.max_output_bytes} ·
                              cleaned {String(step.cleanup_succeeded ?? "—")}
                            </p>
                            {step.evidence ? (
                              <div className="mt-3 grid gap-3 lg:grid-cols-2">
                                <div>
                                  <h4 className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
                                    stdout
                                  </h4>
                                  <pre className="mt-1 max-h-40 overflow-auto rounded-lg bg-slate-950 p-3 text-xs whitespace-pre-wrap text-slate-100">
                                    {step.evidence.stdout || "(empty)"}
                                  </pre>
                                </div>
                                <div>
                                  <h4 className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
                                    stderr
                                  </h4>
                                  <pre className="mt-1 max-h-40 overflow-auto rounded-lg bg-slate-950 p-3 text-xs whitespace-pre-wrap text-slate-100">
                                    {step.evidence.stderr || "(empty)"}
                                  </pre>
                                </div>
                              </div>
                            ) : null}
                          </li>
                        ))}
                      </ol>
                      {run.result ? (
                        <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm">
                          <h4 className="font-semibold text-slate-950">
                            Aggregate Result: {run.result.verdict}
                          </h4>
                          <p className="mt-2 text-slate-700">
                            Evidence {run.result.evidence_references.length} ·
                            redactions {run.result.redaction_count} · artifacts{" "}
                            {run.result.artifact_count} · cleanup{" "}
                            {String(run.result.cleanup_succeeded)} · source
                            invariant {String(run.result.source_invariant)} ·
                            canonical Workspace invariant{" "}
                            {String(run.result.canonical_workspace_invariant)}
                          </p>
                          <p className="mt-2 font-mono text-xs break-all text-slate-600">
                            {run.result.aggregate_digest}
                          </p>
                        </div>
                      ) : null}
                      <div className="mt-5 flex flex-wrap items-center gap-3">
                        {activeSuiteStates.has(run.state) &&
                        run.state !== "cancel_requested" ? (
                          <button
                            type="button"
                            className="rounded-lg px-3 py-2 text-sm font-semibold text-red-700 ring-1 ring-red-300 disabled:opacity-50"
                            disabled={Boolean(busy)}
                            onClick={() => void cancelSuite(run)}
                          >
                            {busy === `cancel-suite-${run.id}`
                              ? "取消中…"
                              : "Cancel Suite"}
                          </button>
                        ) : null}
                        {retryable ? (
                          <>
                            <button
                              type="button"
                              className="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 ring-1 ring-blue-300 disabled:opacity-50"
                              disabled={
                                Boolean(busy) ||
                                !retryGrant ||
                                run.attempt_number >= run.max_attempts
                              }
                              onClick={() =>
                                retryGrant
                                  ? void retrySuite(run, retryGrant)
                                  : undefined
                              }
                            >
                              {busy === `retry-suite-${run.id}`
                                ? "重试中…"
                                : "Retry failed steps"}
                            </button>
                            {!retryGrant ? (
                              <button
                                type="button"
                                className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 ring-1 ring-slate-300 disabled:opacity-50"
                                disabled={
                                  Boolean(busy) ||
                                  run.attempt_number >= run.max_attempts
                                }
                                onClick={() => void requestRetryGrant(run)}
                              >
                                {busy === `retry-grant-${run.id}`
                                  ? "申请中…"
                                  : "Request lineage-bound retry Grant"}
                              </button>
                            ) : null}
                            {run.attempt_number >= run.max_attempts ? (
                              <span className="text-xs text-slate-600">
                                Retry disabled: attempt budget exhausted。
                              </span>
                            ) : null}
                          </>
                        ) : null}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section className="mt-10">
            <h2 className="text-2xl font-semibold text-slate-950">
              4. First-slice 单步记录
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
