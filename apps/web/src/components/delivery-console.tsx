"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
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
import { localizeApiError, localizeErrorCode } from "@/lib/localization";

import { StatusPill } from "./status-pill";

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
  const locale = useLocale();
  const t = useTranslations("delivery");
  const commonT = useTranslations("common");
  const errorT = useTranslations("errors");
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
      setError(localizeApiError(reason, errorT));
      setState("error");
    }
  }, [errorT]);

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
      setError(localizeApiError(reason, errorT));
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
      setError(localizeApiError(reason, errorT));
    } finally {
      setBusy("");
    }
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="border-b border-slate-200 pb-8">
        <p className="text-sm font-semibold tracking-widest text-blue-700 uppercase">
          {t("eyebrow")}
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          {t("title")}
        </h1>
        <p className="mt-3 max-w-4xl text-base leading-7 font-semibold text-slate-800">
          {t("description")}
        </p>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
          {t("boundary")}
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
              {commonT("actions.retry")}
            </button>
          ) : null}
        </div>
      ) : null}

      {state === "loading" ? (
        <p className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">
          {t("loading")}
        </p>
      ) : null}

      {state === "ready" ? (
        <>
          <section className="mt-8 rounded-2xl border border-blue-200 bg-blue-50/60 p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-950">
                  {t("createTitle")}
                </h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
                  {t("createHelp")}
                </p>
              </div>
              <Link
                href="/reviews"
                className="rounded-lg border border-blue-300 bg-white px-3 py-2 text-sm font-semibold text-blue-800 outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
              >
                {t("backReviews")}
              </Link>
            </div>
            {candidates.length === 0 ? (
              <p className="mt-5 rounded-xl border border-dashed border-blue-300 p-4 text-sm text-slate-700">
                {t("noCandidates")}
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
                      {t("candidate", {
                        generation: reviewPackage.freshness_generation,
                        checkpoint: reviewPackage.checkpoint_id,
                      })}
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
                        ? t("binding")
                        : t("createAuthorization")}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-semibold text-slate-950">
              {t("lifecycleTitle")}
            </h2>
            {authorizations.length === 0 ? (
              <p className="mt-4 rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600">
                {t("empty")}
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
                            {t("baseline")}
                          </dt>
                          <dd className="mt-1 font-mono text-xs break-all text-slate-600">
                            {t("package", {
                              digest: authorization.package_digest,
                            })}
                          </dd>
                          <dd className="mt-1 text-slate-600">
                            {t("generationExpires", {
                              generation: authorization.freshness_generation,
                              expires: formatTimestamp(
                                authorization.expires_at,
                                locale,
                              ),
                            })}
                          </dd>
                        </div>
                        <div>
                          <dt className="font-semibold text-slate-700">
                            {t("fixedOperation")}
                          </dt>
                          <dd className="mt-1 text-slate-700">
                            {authorization.commit_message}
                          </dd>
                          <dd className="mt-1 font-semibold text-emerald-800">
                            {t("localOnly")}
                          </dd>
                        </div>
                      </dl>

                      {authorization.error_code ? (
                        <p className="mt-4 text-sm font-semibold break-words text-red-800">
                          {localizeErrorCode(authorization.error_code, errorT)}
                        </p>
                      ) : null}

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
                            {t("approve")}
                          </button>
                          <label className="min-w-60 flex-1 text-sm font-semibold text-slate-700">
                            {t("rejectionReason")}
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
                            {t("reject")}
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
                            ? t("previewing")
                            : authorization.status === "approved"
                              ? t("reviewPreview")
                              : t("reviewRetry")}
                        </button>
                      ) : null}

                      {preview ? (
                        <section className="mt-5 rounded-xl border border-blue-200 bg-blue-50/60 p-4">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <h4 className="font-semibold text-slate-950">
                                {t("manifest", {
                                  attempt:
                                    preview.next_attempt_number ??
                                    t("blockedAttempt"),
                                })}
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
                              {preview.can_dispatch
                                ? t("confirmable")
                                : t("blocked")}
                            </StatusPill>
                          </div>
                          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                            <div>
                              <dt className="font-semibold text-slate-700">
                                {t("gitProof")}
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
                                {t("diffClosure")}
                              </dt>
                              <dd className="mt-1 text-slate-700">
                                {t("diffSummary", {
                                  count: preview.manifest.changed_file_count,
                                  bytes: preview.manifest.total_diff_bytes,
                                })}
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
                            {t("localBoundary")}
                          </p>
                          {preview.blocking_code ? (
                            <p className="mt-3 text-sm font-semibold break-words text-red-800">
                              {localizeErrorCode(preview.blocking_code, errorT)}
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
                            {t("confirmDigest")}
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
                                ? t("dispatching")
                                : preview.retry_of_dispatch_id
                                  ? t("retryExact")
                                  : t("dispatchConfirmed")}
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
                              {t("closePreview")}
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
                          {t("cancelActive")}
                        </button>
                      ) : null}

                      {authorization.dispatches.length > 0 ? (
                        <section className="mt-5 border-t border-slate-100 pt-5">
                          <h4 className="font-semibold text-slate-950">
                            {t("history")}
                          </h4>
                          <ol className="mt-3 space-y-3">
                            {authorization.dispatches.map((dispatch) => (
                              <li
                                key={dispatch.id}
                                className="rounded-lg border border-slate-200 p-3 text-sm"
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <span className="font-semibold text-slate-900">
                                    {t("attempt", {
                                      number: dispatch.attempt_number,
                                    })}
                                  </span>
                                  <StatusPill
                                    tone={statusTone(dispatch.status)}
                                  >
                                    {dispatch.status}
                                  </StatusPill>
                                </div>
                                <p className="mt-2 font-mono text-xs break-all text-slate-600">
                                  {t("manifestDigest", {
                                    digest: dispatch.manifest_digest,
                                  })}
                                </p>
                                {dispatch.error_code ? (
                                  <p className="mt-2 font-semibold break-words text-red-800">
                                    {localizeErrorCode(
                                      dispatch.error_code,
                                      errorT,
                                      dispatch.request_id,
                                    )}
                                  </p>
                                ) : null}
                                <Link
                                  href={`/runners/jobs/${dispatch.runner_job_id}`}
                                  className="mt-2 inline-block font-semibold text-blue-700 underline outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                                >
                                  {t("openEvidence")}
                                </Link>
                              </li>
                            ))}
                          </ol>
                        </section>
                      ) : null}

                      {authorization.delivery ? (
                        <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                          <p className="font-semibold text-emerald-950">
                            {t("commitCreated")}
                          </p>
                          <p className="mt-2 font-mono text-xs break-all text-emerald-900">
                            {authorization.delivery.commit_oid}
                          </p>
                          <p className="mt-1 text-sm text-emerald-900">
                            {t("sourceUnchanged")}
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
