"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  createReviewPackage,
  decideReviewPackage,
  evaluateReleaseReadiness,
  listReviewPackages,
  listValidationSuiteRuns,
  refreshReviewPackage,
  type ReviewPackage,
  type ValidationSuiteRun,
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

function manifestEntries(reviewPackage: ReviewPackage) {
  const entries = reviewPackage.evidence_manifest.entries;
  return Array.isArray(entries)
    ? entries.filter(
        (entry): entry is Record<string, unknown> =>
          typeof entry === "object" && entry !== null,
      )
    : [];
}

export function ReviewConsole() {
  const [suiteRuns, setSuiteRuns] = useState<ValidationSuiteRun[]>([]);
  const [packages, setPackages] = useState<ReviewPackage[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [rejectionReasons, setRejectionReasons] = useState<
    Record<string, string>
  >({});

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [nextSuiteRuns, nextPackages] = await Promise.all([
        listValidationSuiteRuns(),
        listReviewPackages(),
      ]);
      setSuiteRuns(nextSuiteRuns);
      setPackages(nextPackages);
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

  const candidates = useMemo(
    () =>
      suiteRuns.filter(
        (run) =>
          run.state === "succeeded" &&
          run.result?.verdict === "succeeded" &&
          !packages.some((item) => item.suite_run_id === run.id),
      ),
    [packages, suiteRuns],
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
          Governed Final Review
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          Review & Release Readiness
        </h1>
        <p className="mt-3 max-w-4xl text-base leading-7 font-semibold text-slate-800">
          将最新成功 Validation Suite 的精确 Evidence 链封装为不可变 Review
          Package，完成一次人工 Review Decision，再由系统确定性计算 Release
          Readiness。
        </p>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
          Approval 仅是治理决定；它不会授予 commit、push、PR、merge、tag 或
          deployment 权限。基线或 Evidence 变旧后，ready 会立即失效。
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
          正在验证 Suite Evidence 与 Review freshness…
        </p>
      ) : null}

      {state === "ready" ? (
        <>
          <section className="mt-8 rounded-2xl border border-blue-200 bg-blue-50/60 p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">
                  1. 创建 immutable Review Package
                </h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
                  仅列出尚未封装的最新成功 Suite Result。Package
                  不复制原始输出，只保存有序 identity/digest Evidence Manifest。
                </p>
              </div>
              <Link
                href="/validations"
                className="rounded-lg border border-blue-300 bg-white px-3 py-2 text-sm font-semibold text-blue-800 outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
              >
                返回 Validations
              </Link>
            </div>
            {candidates.length === 0 ? (
              <p className="mt-5 rounded-xl border border-dashed border-blue-300 p-4 text-sm text-slate-700">
                当前没有待封装的成功 Suite Result。
              </p>
            ) : (
              <ul className="mt-5 grid gap-4 lg:grid-cols-2">
                {candidates.map((run) => (
                  <li
                    key={run.id}
                    className="rounded-xl border border-blue-200 bg-white p-4"
                  >
                    <p className="font-mono text-xs break-all text-slate-600">
                      {run.id}
                    </p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      {run.suite_id}:v{run.suite_version} · checkpoint{" "}
                      {run.checkpoint_id}
                    </p>
                    <button
                      type="button"
                      className="mt-4 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white outline-none hover:bg-blue-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:opacity-50"
                      disabled={Boolean(busy)}
                      onClick={() =>
                        void perform(`package-${run.id}`, () =>
                          createReviewPackage(
                            { suite_run_id: run.id },
                            `review-package-${run.id}-${crypto.randomUUID()}`,
                          ),
                        )
                      }
                    >
                      {busy === `package-${run.id}`
                        ? "正在封装…"
                        : "Create immutable Review Package"}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-semibold text-slate-950">
              2. Review Decision 与 Readiness
            </h2>
            {packages.length === 0 ? (
              <p className="mt-4 rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600">
                尚无 Review Package。
              </p>
            ) : (
              <ul className="mt-5 space-y-5">
                {packages.map((reviewPackage) => {
                  const entries = manifestEntries(reviewPackage);
                  const rejectedReason =
                    rejectionReasons[reviewPackage.id] ?? "";
                  return (
                    <li
                      key={reviewPackage.id}
                      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-mono text-xs break-all text-slate-500">
                            {reviewPackage.id}
                          </p>
                          <h3 className="mt-2 text-lg font-semibold text-slate-950">
                            Evidence Manifest {entries.length}/2
                          </h3>
                        </div>
                        <StatusPill
                          tone={
                            reviewPackage.freshness === "fresh"
                              ? "positive"
                              : "negative"
                          }
                        >
                          {reviewPackage.freshness}
                        </StatusPill>
                      </div>
                      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                        <div>
                          <dt className="font-semibold text-slate-700">
                            Freshness generation
                          </dt>
                          <dd className="mt-1 text-slate-700">
                            Generation {reviewPackage.freshness_generation} /
                            current {reviewPackage.current_freshness_generation}
                          </dd>
                        </div>
                        <div>
                          <dt className="font-semibold text-slate-700">
                            Trusted blocker summary
                          </dt>
                          <dd className="mt-1 text-slate-700">
                            Critical {reviewPackage.critical_count} · High{" "}
                            {reviewPackage.high_count} · Blocking medium{" "}
                            {reviewPackage.blocking_medium_count}
                          </dd>
                          <dd className="mt-1 font-mono text-xs break-all text-slate-500">
                            {reviewPackage.blocker_source}:v
                            {reviewPackage.blocker_source_version}
                          </dd>
                        </div>
                        <div>
                          <dt className="font-semibold text-slate-700">
                            Package digest
                          </dt>
                          <dd className="mt-1 font-mono text-xs break-all text-slate-600">
                            {reviewPackage.package_digest}
                          </dd>
                        </div>
                        <div>
                          <dt className="font-semibold text-slate-700">
                            Manifest digest
                          </dt>
                          <dd className="mt-1 font-mono text-xs break-all text-slate-600">
                            {reviewPackage.evidence_manifest_digest}
                          </dd>
                        </div>
                      </dl>
                      <ol className="mt-4 grid gap-2 sm:grid-cols-2">
                        {entries.map((entry) => (
                          <li
                            key={String(entry.evidence_id)}
                            className="rounded-lg bg-slate-50 p-3 text-xs text-slate-700"
                          >
                            <span className="font-semibold">
                              {String(entry.sequence)}. {String(entry.step_id)}
                            </span>
                            <span className="mt-1 block font-mono break-all">
                              Evidence {String(entry.evidence_id)}
                            </span>
                          </li>
                        ))}
                      </ol>
                      <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-950">
                        Git authorization: false · Deployment authorization:
                        false
                      </p>
                      {reviewPackage.stale_reason_code ? (
                        <p className="mt-3 text-sm font-semibold text-red-800">
                          Stale: {reviewPackage.stale_reason_code}
                        </p>
                      ) : null}
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-800 outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:opacity-50"
                          disabled={Boolean(busy)}
                          onClick={() =>
                            void perform(`freshness-${reviewPackage.id}`, () =>
                              refreshReviewPackage(reviewPackage.id),
                            )
                          }
                        >
                          Recheck freshness
                        </button>
                        {!reviewPackage.decision &&
                        reviewPackage.freshness === "fresh" ? (
                          <button
                            type="button"
                            className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 disabled:opacity-50"
                            disabled={Boolean(busy)}
                            onClick={() =>
                              void perform(`approve-${reviewPackage.id}`, () =>
                                decideReviewPackage(
                                  reviewPackage.id,
                                  {
                                    decision: "approve",
                                    reason:
                                      "Reviewed exact immutable Evidence Manifest.",
                                    expected_generation:
                                      reviewPackage.freshness_generation,
                                  },
                                  `review-decision-${reviewPackage.id}-g${reviewPackage.freshness_generation}-approve`,
                                ),
                              )
                            }
                          >
                            Approve Review Package
                          </button>
                        ) : null}
                      </div>
                      {!reviewPackage.decision &&
                      reviewPackage.freshness === "fresh" ? (
                        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                          <label className="flex-1 text-sm font-semibold text-slate-700">
                            Rejection reason
                            <input
                              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-200"
                              value={rejectedReason}
                              onChange={(event) =>
                                setRejectionReasons((current) => ({
                                  ...current,
                                  [reviewPackage.id]: event.currentTarget.value,
                                }))
                              }
                            />
                          </label>
                          <button
                            type="button"
                            className="self-end rounded-lg border border-red-300 px-3 py-2 text-sm font-semibold text-red-800 outline-none focus-visible:ring-2 focus-visible:ring-red-600 disabled:opacity-50"
                            disabled={Boolean(busy) || !rejectedReason.trim()}
                            onClick={() =>
                              void perform(`reject-${reviewPackage.id}`, () =>
                                decideReviewPackage(
                                  reviewPackage.id,
                                  {
                                    decision: "reject",
                                    reason: rejectedReason,
                                    expected_generation:
                                      reviewPackage.freshness_generation,
                                  },
                                  `review-decision-${reviewPackage.id}-g${reviewPackage.freshness_generation}-reject`,
                                ),
                              )
                            }
                          >
                            Reject Review Package
                          </button>
                        </div>
                      ) : null}
                      {reviewPackage.decision ? (
                        <div className="mt-4 rounded-xl border border-slate-200 p-4">
                          <p className="text-sm font-semibold text-slate-900">
                            Decision: {reviewPackage.decision.decision} ·{" "}
                            {formatTimestamp(reviewPackage.decision.created_at)}
                          </p>
                          {!reviewPackage.readiness ? (
                            <button
                              type="button"
                              className="mt-3 rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-slate-700 disabled:opacity-50"
                              disabled={Boolean(busy)}
                              onClick={() =>
                                void perform(
                                  `readiness-${reviewPackage.id}`,
                                  () =>
                                    evaluateReleaseReadiness(reviewPackage.id),
                                )
                              }
                            >
                              Compute deterministic Readiness
                            </button>
                          ) : (
                            <p className="mt-2 text-sm font-semibold text-slate-800">
                              Release Readiness:{" "}
                              {reviewPackage.readiness.effective_verdict}
                            </p>
                          )}
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
