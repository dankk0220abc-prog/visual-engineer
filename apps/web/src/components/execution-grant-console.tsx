"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  createExecutionGrant,
  decideExecutionGrant,
  listEligibleExecutionContexts,
  listExecutionGrants,
  revokeExecutionGrant,
  type EligibleExecutionContext,
  type ExecutionGrant,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";

import { StatusPill } from "./status-pill";

function message(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.code}: ${error.message}${
      error.requestId ? `（请求 ID：${error.requestId}）` : ""
    }`;
  }
  return "出现未预期的错误。";
}

function grantTone(
  status: ExecutionGrant["status"],
): "neutral" | "positive" | "negative" | "pending" {
  if (status === "approved") return "positive";
  if (status === "pending") return "pending";
  if (status === "rejected" || status === "revoked") return "negative";
  return "neutral";
}

export function ExecutionGrantConsole() {
  const [contexts, setContexts] = useState<EligibleExecutionContext[]>([]);
  const [grants, setGrants] = useState<ExecutionGrant[]>([]);
  const [selected, setSelected] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [rejectReason, setRejectReason] = useState<Record<string, string>>({});

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [nextContexts, nextGrants] = await Promise.all([
        listEligibleExecutionContexts(),
        listExecutionGrants(),
      ]);
      setContexts(nextContexts);
      setGrants(nextGrants);
      setSelected((current) => current || nextContexts[0]?.plan_id || "");
      setState("ready");
    } catch (reason) {
      setError(message(reason));
      setState("error");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([listEligibleExecutionContexts(), listExecutionGrants()])
      .then(([nextContexts, nextGrants]) => {
        if (cancelled) return;
        setContexts(nextContexts);
        setGrants(nextGrants);
        setSelected(nextContexts[0]?.plan_id || "");
        setState("ready");
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setError(message(reason));
        setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedContext = useMemo(
    () => contexts.find((context) => context.plan_id === selected) ?? null,
    [contexts, selected],
  );

  async function createGrant() {
    if (!selectedContext) return;
    setBusy("create");
    setError("");
    try {
      await createExecutionGrant({
        plan_id: selectedContext.plan_id,
        repository_handle_id: selectedContext.repository_handle_id,
      });
      await refresh();
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy("");
    }
  }

  async function decide(grant: ExecutionGrant, decision: "approve" | "reject") {
    setBusy(`${decision}-${grant.id}`);
    setError("");
    try {
      await decideExecutionGrant(grant.id, {
        decision,
        reason:
          decision === "reject"
            ? rejectReason[grant.id] || undefined
            : "Fixture-only grant reviewed in the local browser.",
      });
      await refresh();
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy("");
    }
  }

  async function revoke(grant: ExecutionGrant) {
    setBusy(`revoke-${grant.id}`);
    setError("");
    try {
      await revokeExecutionGrant(grant.id);
      await refresh();
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy("");
    }
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="border-b border-slate-200 pb-8">
        <p className="text-sm font-semibold tracking-widest text-blue-700 uppercase">
          Independent execution authority
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          Execution Grants
        </h1>
        <p className="mt-3 max-w-4xl text-base leading-7 font-semibold text-slate-800">
          Plan approval does not authorize execution. This Execution Grant is a
          separate human decision.
        </p>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          策略由服务器从 approved Plan 与当前 Repository Handle
          收窄生成；浏览器不能提交 Shell、主机路径或扩大后的权限。
        </p>
      </header>

      {state === "loading" ? (
        <p className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">
          正在加载授权上下文…
        </p>
      ) : null}
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

      {state === "ready" ? (
        <>
          <section className="mt-8 rounded-2xl border border-blue-200 bg-blue-50/60 p-5 sm:p-6">
            <h2 className="text-xl font-semibold text-slate-950">
              从 eligible Plan 创建 pending Grant
            </h2>
            {contexts.length === 0 ? (
              <p className="mt-3 text-sm text-slate-700">
                当前没有 revision 一致的 approved Plan 与 available Repository。
              </p>
            ) : (
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
                <label className="min-w-0 flex-1 text-sm font-semibold text-slate-800">
                  Approved execution context
                  <select
                    className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-200"
                    value={selected}
                    onChange={(event) => setSelected(event.currentTarget.value)}
                  >
                    {contexts.map((context) => (
                      <option key={context.plan_id} value={context.plan_id}>
                        {context.task_title} · Plan v{context.plan_version} ·{" "}
                        {context.repository_display_name}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-blue-800 focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2 disabled:opacity-50"
                  disabled={!selectedContext || busy === "create"}
                  onClick={() => void createGrant()}
                >
                  {busy === "create" ? "创建中…" : "创建 pending Grant"}
                </button>
              </div>
            )}
          </section>

          {grants.length === 0 ? (
            <section className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
              <h2 className="font-semibold text-slate-900">
                暂无 Execution Grant
              </h2>
              <p className="mt-2 text-sm text-slate-600">
                选择上方 approved context 创建第一条独立授权。
              </p>
            </section>
          ) : (
            <ul className="mt-8 space-y-6">
              {grants.map((grant) => (
                <li
                  key={grant.id}
                  className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
                        {grant.repository_display_name}
                      </p>
                      <h2 className="mt-1 font-mono text-sm break-all text-slate-950">
                        {grant.id}
                      </h2>
                    </div>
                    <StatusPill tone={grantTone(grant.status)}>
                      {grant.status}
                    </StatusPill>
                  </div>

                  <dl className="mt-5 grid gap-4 text-sm md:grid-cols-2 xl:grid-cols-3">
                    <div>
                      <dt className="font-semibold text-slate-500">Plan</dt>
                      <dd className="mt-1 font-mono text-xs break-all">
                        {grant.plan_id}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">Snapshot</dt>
                      <dd className="mt-1 font-mono text-xs break-all">
                        {grant.snapshot_fingerprint}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        Source revision
                      </dt>
                      <dd className="mt-1 font-mono text-xs break-all">
                        {grant.source_revision}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        Allowed operations
                      </dt>
                      <dd className="mt-1 break-words">
                        {grant.allowed_operations.join(" · ")}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        Allowed paths
                      </dt>
                      <dd className="mt-1 font-mono text-xs break-all">
                        {grant.allowed_paths.join(", ")}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        Denied paths
                      </dt>
                      <dd className="mt-1 max-h-24 overflow-y-auto font-mono text-xs break-all">
                        {grant.denied_paths.join(", ")}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">Budgets</dt>
                      <dd className="mt-1">
                        {grant.max_files_changed} files ·{" "}
                        {grant.max_total_write_bytes} total bytes ·{" "}
                        {grant.max_single_file_bytes} per file ·{" "}
                        {grant.max_diff_bytes} diff bytes
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        Workspace TTL
                      </dt>
                      <dd className="mt-1">{grant.workspace_ttl_seconds}s</dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-500">
                        Explicit denials
                      </dt>
                      <dd className="mt-1">
                        network {grant.network_policy} · Shell{" "}
                        {String(grant.shell_access)} · source write{" "}
                        {String(grant.source_repository_write_access)} · Git
                        delivery {String(grant.git_delivery_access)}
                      </dd>
                    </div>
                    <div className="md:col-span-2 xl:col-span-3">
                      <dt className="font-semibold text-slate-500">
                        Canonical policy hash
                      </dt>
                      <dd className="mt-1 font-mono text-xs break-all">
                        {grant.policy_hash}
                      </dd>
                    </div>
                  </dl>

                  <p className="mt-5 text-xs text-slate-500">
                    Requested {formatTimestamp(grant.requested_at)} · expires{" "}
                    {formatTimestamp(grant.expires_at)}
                  </p>
                  {grant.status === "pending" ? (
                    <div className="mt-5 grid gap-3 border-t border-slate-200 pt-5 sm:grid-cols-[auto_minmax(12rem,1fr)_auto]">
                      <button
                        type="button"
                        className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 focus-visible:ring-offset-2 disabled:opacity-50"
                        disabled={Boolean(busy)}
                        onClick={() => void decide(grant, "approve")}
                      >
                        {busy === `approve-${grant.id}`
                          ? "批准中…"
                          : "Approve Grant"}
                      </button>
                      <label className="text-sm font-semibold text-slate-700">
                        Reject reason
                        <input
                          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-red-600 focus:ring-2 focus:ring-red-100"
                          value={rejectReason[grant.id] ?? ""}
                          onChange={(event) =>
                            setRejectReason((current) => ({
                              ...current,
                              [grant.id]: event.currentTarget.value,
                            }))
                          }
                        />
                      </label>
                      <button
                        type="button"
                        className="self-end rounded-lg px-4 py-2 text-sm font-semibold text-red-700 ring-1 ring-red-300 outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-50"
                        disabled={
                          Boolean(busy) ||
                          !(rejectReason[grant.id] ?? "").trim()
                        }
                        onClick={() => void decide(grant, "reject")}
                      >
                        Reject
                      </button>
                    </div>
                  ) : null}
                  {grant.status === "approved" ? (
                    <div className="mt-5 flex flex-wrap gap-3 border-t border-slate-200 pt-5">
                      <Link
                        href="/workspaces"
                        className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-700"
                      >
                        创建或查看 Workspace
                      </Link>
                      <button
                        type="button"
                        className="rounded-lg px-4 py-2 text-sm font-semibold text-red-700 ring-1 ring-red-300 outline-none focus-visible:ring-2 focus-visible:ring-red-700 disabled:opacity-50"
                        disabled={Boolean(busy)}
                        onClick={() => void revoke(grant)}
                      >
                        Revoke
                      </button>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </>
      ) : null}
    </main>
  );
}
