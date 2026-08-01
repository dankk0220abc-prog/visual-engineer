"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  createDeliveryAuthorization,
  decideDeliveryAuthorization,
  dispatchLocalDelivery,
  listDeliveryAuthorizations,
  listReviewPackages,
  type DeliveryAuthorization,
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
          Governed Local Delivery
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          Local Branch & Commit
        </h1>
        <p className="mt-3 max-w-4xl text-base leading-7 font-semibold text-slate-800">
          将 fresh、approved、ready 的 Review
          基线绑定到一次独立的人工交付授权，再由 Runner 在隔离 fixture workspace
          中创建系统命名的本地分支和单个 commit。
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
              2. 单独批准并执行本地交付
            </h2>
            {authorizations.length === 0 ? (
              <p className="mt-4 rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600">
                尚无 Delivery Authorization。
              </p>
            ) : (
              <ul className="mt-5 space-y-5">
                {authorizations.map((authorization) => {
                  const reason = rejectionReasons[authorization.id] ?? "";
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

                      {authorization.status === "approved" ? (
                        <button
                          type="button"
                          className="mt-5 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white outline-none hover:bg-blue-800 focus-visible:ring-2 focus-visible:ring-blue-600 disabled:opacity-50"
                          disabled={Boolean(busy)}
                          onClick={() =>
                            void perform(`dispatch-${authorization.id}`, () =>
                              dispatchLocalDelivery(authorization.id),
                            )
                          }
                        >
                          {busy === `dispatch-${authorization.id}`
                            ? "正在派发…"
                            : "Dispatch governed local commit"}
                        </button>
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
