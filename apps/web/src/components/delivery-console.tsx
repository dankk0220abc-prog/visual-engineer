"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  cancelRunnerJob,
  createDeliveryAuthorization,
  decideDeliveryAuthorization,
  dispatchLocalDelivery,
  getDeliveryPreview,
  listDeliveryAuthorizations,
  listReviewPackages,
  type DeliveryAuthorization,
  type DeliveryPreview,
  type ReviewPackage,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";

import { StatusPill } from "./status-pill";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.code}: ${error.message}${
      error.requestId ? `（请求 ID：${error.requestId}）` : ""
    }`;
  }
  return "出现未预期的错误。";
}

function statusTone(status: DeliveryAuthorization["status"]) {
  if (status === "succeeded") return "positive" as const;
  if (
    status === "rejected" ||
    status === "failed" ||
    status === "cancelled" ||
    status === "stale"
  ) {
    return "negative" as const;
  }
  return "neutral" as const;
}

function dispatchIdempotencyKey(
  authorizationId: string,
  preview: DeliveryPreview,
): string {
  return `delivery-dispatch-v1:${authorizationId}:${preview.next_attempt_number}:${preview.manifest.manifest_digest}`;
}

export function DeliveryConsole() {
  const [packages, setPackages] = useState<ReviewPackage[]>([]);
  const [authorizations, setAuthorizations] = useState<DeliveryAuthorization[]>(
    [],
  );
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [rejectionReasons, setRejectionReasons] = useState<
    Record<string, string>
  >({});
  const [previews, setPreviews] = useState<Record<string, DeliveryPreview>>({});
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({});

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [nextPackages, nextAuthorizations] = await Promise.all([
        listReviewPackages(),
        listDeliveryAuthorizations(),
      ]);
      setPackages(nextPackages);
      setAuthorizations(nextAuthorizations);
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
    if (!authorizations.some((item) => item.status === "dispatched")) {
      return;
    }
    const timer = window.setInterval(() => void refresh(), 500);
    return () => window.clearInterval(timer);
  }, [authorizations, refresh]);

  const candidates = useMemo(
    () =>
      packages.filter(
        (item) =>
          item.freshness === "fresh" &&
          item.decision?.decision === "approve" &&
          item.readiness?.verdict === "ready" &&
          !authorizations.some(
            (authorization) =>
              authorization.review_package_id === item.id &&
              authorization.status !== "stale",
          ),
      ),
    [authorizations, packages],
  );

  async function perform(key: string, action: () => Promise<unknown>) {
    setBusy(key);
    setError("");
    try {
      await action();
      setPreviews({});
      setConfirmed({});
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function loadPreview(authorizationId: string) {
    setBusy(`preview-${authorizationId}`);
    setError("");
    try {
      const preview = await getDeliveryPreview(authorizationId);
      setPreviews((current) => ({ ...current, [authorizationId]: preview }));
      setConfirmed((current) => ({ ...current, [authorizationId]: false }));
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
          Governed Local Delivery
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          Local Delivery Lifecycle
        </h1>
        <p className="mt-3 max-w-4xl text-base leading-7 font-semibold text-slate-800">
          将 fresh、approved、ready 的 Review
          基线绑定到一次独立的人工交付授权。派发前必须核对 immutable manifest
          并确认精确 digest；失败或取消后，只能沿同一 manifest 安全重试。
        </p>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
          该授权永远不包含 source repository 写入、remote、push、PR、tag 或
          deploy。Review approval 本身不能触发交付。
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
          正在核对 Review freshness 与 local-only 权限边界…
        </p>
      ) : null}

      {state === "ready" ? (
        <>
          <section className="mt-8 rounded-2xl border border-blue-200 bg-blue-50/60 p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">
                  1. 创建独立 Delivery Authorization
                </h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
                  候选项必须仍是精确的 fresh Review generation、approved
                  decision 与 ready verdict。授权会固定 checkpoint、diff
                  hash、branch ref 和 commit message。
                </p>
              </div>
              <Link
                href="/reviews"
                className="rounded-lg border border-blue-300 bg-white px-3 py-2 text-sm font-semibold text-blue-800 outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
              >
                返回 Reviews
              </Link>
            </div>
            {candidates.length === 0 ? (
              <p className="mt-5 rounded-xl border border-dashed border-blue-300 p-4 text-sm text-slate-700">
                当前没有新的 fresh、approved、ready Review 候选项。
              </p>
            ) : (
              <ul className="mt-5 grid gap-4 lg:grid-cols-2">
                {candidates.map((reviewPackage) => (
                  <li
                    key={reviewPackage.id}
                    className="rounded-xl border border-blue-200 bg-white p-4"
                  >
                    <p className="font-mono text-xs break-all text-slate-600">
                      {reviewPackage.id}
                    </p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      Generation {reviewPackage.freshness_generation} ·
                      checkpoint {reviewPackage.checkpoint_id}
                    </p>
                    <button
                      type="button"
                      className="mt-4 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white outline-none hover:bg-blue-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:opacity-50"
                      disabled={Boolean(busy)}
                      onClick={() =>
                        void perform(`create-${reviewPackage.id}`, () =>
                          createDeliveryAuthorization(
                            { review_package_id: reviewPackage.id },
                            `delivery-authorization-${reviewPackage.id}-${crypto.randomUUID()}`,
                          ),
                        )
                      }
                    >
                      {busy === `create-${reviewPackage.id}`
                        ? "正在绑定…"
                        : "Create Delivery Authorization"}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-semibold text-slate-950">
              2. 批准、预览、确认与恢复
            </h2>
            {authorizations.length === 0 ? (
              <p className="mt-4 rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600">
                尚无 Delivery Authorization。
              </p>
            ) : (
              <ul className="mt-5 space-y-5">
                {authorizations.map((authorization) => {
                  const reason = rejectionReasons[authorization.id] ?? "";
                  const preview = previews[authorization.id];
                  const canReviewDispatch = [
                    "approved",
                    "failed",
                    "cancelled",
                  ].includes(authorization.status);
                  return (
                    <li
                      key={authorization.id}
                      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                      data-testid={`delivery-${authorization.id}`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="font-mono text-xs break-all text-slate-500">
                            {authorization.id}
                          </p>
                          <h3 className="mt-2 text-lg font-semibold break-all text-slate-950">
                            {authorization.branch_ref}
                          </h3>
                        </div>
                        <StatusPill tone={statusTone(authorization.status)}>
                          {authorization.status}
                        </StatusPill>
                      </div>
                      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                        <div>
                          <dt className="font-semibold text-slate-700">
                            Immutable Review baseline
                          </dt>
                          <dd className="mt-1 font-mono text-xs break-all text-slate-600">
                            package {authorization.package_digest}
                          </dd>
                          <dd className="mt-1 text-slate-600">
                            generation {authorization.freshness_generation} ·
                            expires {formatTimestamp(authorization.expires_at)}
                          </dd>
                        </div>
                        <div>
                          <dt className="font-semibold text-slate-700">
                            Fixed local operation
                          </dt>
                          <dd className="mt-1 text-slate-700">
                            {authorization.commit_message}
                          </dd>
                          <dd className="mt-1 font-semibold text-emerald-800">
                            Local commit only · remote/push/PR/tag/deploy denied
                          </dd>
                        </div>
                      </dl>

                      {authorization.status === "pending" ? (
                        <div className="mt-5 flex flex-wrap items-end gap-3 border-t border-slate-100 pt-5">
                          <button
                            type="button"
                            className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white outline-none hover:bg-emerald-800 focus-visible:ring-2 focus-visible:ring-emerald-600 disabled:opacity-50"
                            disabled={Boolean(busy)}
                            onClick={() =>
                              void perform(`approve-${authorization.id}`, () =>
                                decideDeliveryAuthorization(
                                  authorization.id,
                                  { decision: "approve", reason: null },
                                  `delivery-approve-${authorization.id}-${crypto.randomUUID()}`,
                                ),
                              )
                            }
                          >
                            Approve local commit
                          </button>
                          <label className="min-w-60 flex-1 text-sm font-semibold text-slate-700">
                            Rejection reason
                            <input
                              value={reason}
                              onChange={(event) =>
                                setRejectionReasons((current) => ({
                                  ...current,
                                  [authorization.id]: event.target.value,
                                }))
                              }
                              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                            />
                          </label>
                          <button
                            type="button"
                            className="rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 outline-none focus-visible:ring-2 focus-visible:ring-red-600 disabled:opacity-50"
                            disabled={Boolean(busy) || !reason.trim()}
                            onClick={() =>
                              void perform(`reject-${authorization.id}`, () =>
                                decideDeliveryAuthorization(
                                  authorization.id,
                                  { decision: "reject", reason },
                                  `delivery-reject-${authorization.id}-${crypto.randomUUID()}`,
                                ),
                              )
                            }
                          >
                            Reject
                          </button>
                        </div>
                      ) : null}

                      {canReviewDispatch && !preview ? (
                        <button
                          type="button"
                          className="mt-5 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white outline-none hover:bg-blue-800 focus-visible:ring-2 focus-visible:ring-blue-600 disabled:opacity-50"
                          disabled={Boolean(busy)}
                          onClick={() => void loadPreview(authorization.id)}
                        >
                          {busy === `preview-${authorization.id}`
                            ? "正在生成预览…"
                            : authorization.status === "approved"
                              ? "Review delivery preview"
                              : "Review safe retry"}
                        </button>
                      ) : null}

                      {preview ? (
                        <section className="mt-5 rounded-xl border border-blue-200 bg-blue-50/60 p-4">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <h4 className="font-semibold text-slate-950">
                                Immutable delivery manifest · attempt{" "}
                                {preview.next_attempt_number ?? "blocked"}
                              </h4>
                              <p className="mt-1 font-mono text-xs break-all text-slate-600">
                                {preview.manifest.manifest_digest}
                              </p>
                            </div>
                            <StatusPill
                              tone={
                                preview.can_dispatch ? "positive" : "negative"
                              }
                            >
                              {preview.can_dispatch ? "confirmable" : "blocked"}
                            </StatusPill>
                          </div>
                          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                            <div>
                              <dt className="font-semibold text-slate-700">
                                Deterministic Git proof
                              </dt>
                              <dd className="mt-1 break-all text-slate-700">
                                {preview.manifest.branch_ref}
                              </dd>
                              <dd className="mt-1 text-slate-600">
                                {preview.manifest.commit_message}
                              </dd>
                            </div>
                            <div>
                              <dt className="font-semibold text-slate-700">
                                Exact diff closure
                              </dt>
                              <dd className="mt-1 text-slate-700">
                                {preview.manifest.changed_file_count} file(s) ·{" "}
                                {preview.manifest.total_diff_bytes} bytes
                              </dd>
                              <dd className="mt-1 font-mono text-xs break-all text-slate-600">
                                {preview.manifest.checkpoint_diff_hash}
                              </dd>
                            </div>
                          </dl>
                          <ul className="mt-3 list-inside list-disc text-sm text-slate-700">
                            {preview.manifest.changed_paths.map((path) => (
                              <li
                                key={path}
                                className="font-mono text-xs break-all"
                              >
                                {path}
                              </li>
                            ))}
                          </ul>
                          <pre className="mt-4 max-h-72 overflow-auto rounded-lg bg-slate-950 p-3 text-xs whitespace-pre-wrap text-slate-100">
                            {preview.diff_artifact}
                          </pre>
                          <p className="mt-3 text-sm font-semibold text-emerald-900">
                            Local ref only · source write, remote, push, PR, tag
                            and deploy remain denied.
                          </p>
                          {preview.blocking_code ? (
                            <p className="mt-3 text-sm font-semibold text-red-800">
                              {preview.blocking_code}
                            </p>
                          ) : null}
                          <label className="mt-4 flex items-start gap-2 text-sm font-semibold text-slate-800">
                            <input
                              type="checkbox"
                              checked={confirmed[authorization.id] ?? false}
                              disabled={!preview.can_dispatch || Boolean(busy)}
                              onChange={(event) =>
                                setConfirmed((current) => ({
                                  ...current,
                                  [authorization.id]: event.target.checked,
                                }))
                              }
                              className="mt-1"
                            />
                            I confirm this exact manifest digest for local-only
                            delivery.
                          </label>
                          <div className="mt-4 flex flex-wrap gap-3">
                            <button
                              type="button"
                              className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white outline-none hover:bg-blue-800 focus-visible:ring-2 focus-visible:ring-blue-600 disabled:opacity-50"
                              disabled={
                                Boolean(busy) ||
                                !preview.can_dispatch ||
                                !confirmed[authorization.id]
                              }
                              onClick={() =>
                                void perform(
                                  `dispatch-${authorization.id}`,
                                  () =>
                                    dispatchLocalDelivery(
                                      authorization.id,
                                      {
                                        confirmation_digest:
                                          preview.manifest.manifest_digest,
                                        retry_of_dispatch_id:
                                          preview.retry_of_dispatch_id,
                                      },
                                      dispatchIdempotencyKey(
                                        authorization.id,
                                        preview,
                                      ),
                                    ),
                                )
                              }
                            >
                              {busy === `dispatch-${authorization.id}`
                                ? "正在派发…"
                                : preview.retry_of_dispatch_id
                                  ? "Retry exact local delivery"
                                  : "Dispatch confirmed local delivery"}
                            </button>
                            <button
                              type="button"
                              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:opacity-50"
                              disabled={Boolean(busy)}
                              onClick={() => {
                                setPreviews((current) => {
                                  const next = { ...current };
                                  delete next[authorization.id];
                                  return next;
                                });
                              }}
                            >
                              Close preview
                            </button>
                          </div>
                        </section>
                      ) : null}

                      {authorization.status === "dispatched" &&
                      authorization.job ? (
                        <button
                          type="button"
                          className="mt-5 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 outline-none focus-visible:ring-2 focus-visible:ring-red-600 disabled:opacity-50"
                          disabled={Boolean(busy)}
                          onClick={() =>
                            void perform(`cancel-${authorization.id}`, () =>
                              cancelRunnerJob(authorization.job!.id),
                            )
                          }
                        >
                          Cancel active delivery
                        </button>
                      ) : null}

                      {authorization.dispatches.length > 0 ? (
                        <section className="mt-5 border-t border-slate-100 pt-5">
                          <h4 className="font-semibold text-slate-950">
                            Dispatch history
                          </h4>
                          <ol className="mt-3 space-y-3">
                            {authorization.dispatches.map((dispatch) => (
                              <li
                                key={dispatch.id}
                                className="rounded-lg border border-slate-200 p-3 text-sm"
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <span className="font-semibold text-slate-900">
                                    Attempt {dispatch.attempt_number}
                                  </span>
                                  <StatusPill
                                    tone={statusTone(dispatch.status)}
                                  >
                                    {dispatch.status}
                                  </StatusPill>
                                </div>
                                <p className="mt-2 font-mono text-xs break-all text-slate-600">
                                  manifest {dispatch.manifest_digest}
                                </p>
                                {dispatch.error_code ? (
                                  <p className="mt-2 font-semibold text-red-800">
                                    {dispatch.error_code}
                                  </p>
                                ) : null}
                                <Link
                                  href={`/runners/jobs/${dispatch.runner_job_id}`}
                                  className="mt-2 inline-block font-semibold text-blue-700 underline outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                                >
                                  Open Runner evidence
                                </Link>
                              </li>
                            ))}
                          </ol>
                        </section>
                      ) : null}

                      {authorization.delivery ? (
                        <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                          <p className="font-semibold text-emerald-950">
                            Local commit created
                          </p>
                          <p className="mt-2 font-mono text-xs break-all text-emerald-900">
                            {authorization.delivery.commit_oid}
                          </p>
                          <p className="mt-1 text-sm text-emerald-900">
                            Source repository unchanged; no remote operation was
                            performed.
                          </p>
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </main>
  );
}
