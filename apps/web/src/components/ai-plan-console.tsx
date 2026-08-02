"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import type { AIPlanRequest } from "@/lib/api";
import {
  localizeAction,
  localizeEval,
  localizeStatus,
} from "@/lib/localization";

import { StatusPill } from "./status-pill";

function TextList({ title, items }: { title: string; items: string[] }) {
  const t = useTranslations("aiPlan");
  return (
    <section>
      <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
      {items.length ? (
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6 text-slate-700">
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-slate-500">{t("noneRecorded")}</p>
      )}
    </section>
  );
}

function operationLabel(
  operation: NonNullable<AIPlanRequest["plan"]>["proposed_operations"][number],
  t: ReturnType<typeof useTranslations>,
): string {
  if (operation.kind === "workspace_text_create_v1") {
    return localizeAction("workspace_text_create_v1", t, {
      path: operation.relative_path,
      intent: operation.intent,
    });
  }
  if (operation.kind === "workspace_text_replace_v1") {
    return localizeAction("workspace_text_replace_v1", t, {
      path: operation.relative_path,
      intent: operation.intent,
    });
  }
  return localizeAction("validation_suite_v1", t, {
    id: operation.suite_id,
    version: operation.suite_version,
  });
}

function statusTone(
  status: AIPlanRequest["status"],
): "positive" | "negative" | "pending" {
  if (status === "generated" || status === "approved") return "positive";
  if (["failed", "cancelled", "stale", "rejected"].includes(status)) {
    return "negative";
  }
  return "pending";
}

export function AIPlanConsole({
  request,
  busy,
  onFreshness,
  onCancel,
  onDecision,
}: {
  request: AIPlanRequest;
  busy: boolean;
  onFreshness: () => Promise<void>;
  onCancel: () => Promise<void>;
  onDecision: (
    decision: "approve" | "reject",
    comment?: string,
  ) => Promise<void>;
}) {
  const t = useTranslations("aiPlan");
  const statusT = useTranslations("common.status");
  const [rejectionReason, setRejectionReason] = useState("");
  const [formError, setFormError] = useState("");
  const plan = request.plan;
  const blockingEvalFailures = request.eval_results.filter(
    (result) => result.severity === "blocking" && !result.passed,
  );

  async function reject() {
    const reason = rejectionReason.trim();
    if (!reason) {
      setFormError(t("rejectValidation"));
      return;
    }
    setFormError("");
    await onDecision("reject", reason);
  }

  return (
    <section
      className="rounded-2xl border border-indigo-200 bg-white p-5 shadow-sm sm:p-7"
      aria-labelledby="ai-plan-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold tracking-widest text-indigo-700 uppercase">
            {t("eyebrow")}
          </p>
          <h2
            id="ai-plan-heading"
            className="mt-1 text-xl font-semibold text-slate-950"
          >
            {t("title")}
          </h2>
        </div>
        <StatusPill tone={statusTone(request.status)}>
          {request.status}
        </StatusPill>
      </div>

      <div className="mt-5 rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm leading-6 text-indigo-950">
        <p className="font-semibold">{t("approvalBoundary")}</p>
        <p className="mt-1">{t("authorityHelp")}</p>
        <p className="mt-1">{t("outputBoundary")}</p>
      </div>

      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        {[
          [t("provider"), request.provider_id],
          [
            t("prompt"),
            `${request.prompt_template_id} · ${request.prompt_version}`,
          ],
          [
            t("context"),
            t("contextSummary", {
              count: request.context_reference_count,
              bytes: request.context_bytes,
            }),
          ],
          [t("retries"), String(request.retry_count)],
          [t("sourceRevision"), request.source_revision],
          [t("snapshot"), request.snapshot_fingerprint],
          [t("promptDigest"), request.prompt_digest],
          [t("requestDigest"), request.request_digest],
          [t("planDigest"), request.deterministic_digest ?? t("notAvailable")],
        ].map(([label, value]) => (
          <div key={label} className="min-w-0 rounded-xl bg-slate-50 p-3">
            <dt className="text-xs font-semibold tracking-wide text-slate-500 uppercase">
              {label}
            </dt>
            <dd className="mt-1 font-mono text-xs break-all text-slate-900">
              {value}
            </dd>
          </div>
        ))}
      </dl>

      <section className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <h3 className="text-sm font-semibold text-slate-950">
          {t("capabilities")}
        </h3>
        <dl className="mt-3 grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
          {[
            [
              t("implementation"),
              request.provider_metadata.implementation_version,
            ],
            [t("modelLabel"), request.provider_metadata.model_label],
            [
              t("determinismReplay"),
              `${request.provider_metadata.deterministic} / ${request.provider_metadata.fixture_replay}`,
            ],
            [
              t("structuredOutput"),
              String(request.provider_metadata.structured_output),
            ],
            [
              t("networkAccess"),
              String(request.provider_metadata.network_access),
            ],
            [
              t("credentialsRequired"),
              String(request.provider_metadata.credentials_required),
            ],
            [t("billingBasis"), request.provider_metadata.billing_basis],
            [
              t("contextOutputLimits"),
              `${request.provider_metadata.max_context_bytes} / ${request.provider_metadata.max_output_bytes} bytes`,
            ],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="font-semibold text-slate-500">{label}</dt>
              <dd className="mt-1 font-mono break-all text-slate-800">
                {value}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      {request.status === "generating" || request.status === "requested" ? (
        <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-900" role="status">
            {t("generationPending")}
          </p>
          <button
            type="button"
            disabled={busy}
            onClick={() => void onCancel()}
            className="mt-3 rounded-xl border border-amber-300 bg-white px-4 py-2.5 text-sm font-semibold text-amber-950 outline-none hover:bg-amber-100 focus-visible:ring-2 focus-visible:ring-amber-700 focus-visible:ring-offset-2 disabled:opacity-60"
          >
            {t("cancelGeneration")}
          </button>
        </div>
      ) : null}

      {request.error_message ? (
        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <p className="font-semibold">{request.error_code ?? t("failed")}</p>
          <p className="mt-1">{request.error_message}</p>
        </div>
      ) : null}

      {blockingEvalFailures.length ? (
        <div
          className="mt-5 rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-950"
          role="alert"
        >
          <p className="font-semibold">{t("evalBlocked")}</p>
          <p className="mt-1">{t("evalBlockedHelp")}</p>
        </div>
      ) : null}

      {plan ? (
        <div className="mt-7 space-y-7">
          <section>
            <h3 className="text-sm font-semibold text-slate-500 uppercase">
              {t("requirementSummary")}
            </h3>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-800">
              {plan.requirement_summary}
            </p>
          </section>

          <div className="grid gap-6 md:grid-cols-2">
            <TextList
              title={t("repositoryFindings")}
              items={plan.repository_findings.map(
                (finding) =>
                  `${finding.kind}: ${finding.summary} [${finding.context_reference_ids.join(", ")}]`,
              )}
            />
            <TextList title={t("assumptions")} items={plan.assumptions} />
            <TextList
              title={t("expectedChanges")}
              items={plan.expected_changes.map(
                (change) =>
                  `${change.change_type} ${change.relative_path} · ${change.component}: ${change.rationale}`,
              )}
            />
            <TextList
              title={t("operations")}
              items={plan.proposed_operations.map((operation) =>
                operationLabel(operation, t),
              )}
            />
            <TextList
              title={t("validationSuites")}
              items={plan.validation_suites.map(
                (suite) =>
                  `${suite.suite_id}: ${suite.name} · ${t("requiredChecks", {
                    count: suite.checks.length,
                  })}`,
              )}
            />
            <TextList
              title={t("risks")}
              items={plan.risks.map(
                (risk) =>
                  `${risk.severity} · ${risk.summary} ${t("mitigation", {
                    value: risk.mitigation,
                  })}`,
              )}
            />
            <TextList
              title={t("acceptanceCriteria")}
              items={plan.acceptance_criteria.map(
                (criterion) =>
                  `${criterion.statement} [${criterion.validation_suite_ids.join(", ")}]`,
              )}
            />
            <TextList
              title={t("unresolvedQuestions")}
              items={plan.unresolved_questions}
            />
          </div>
        </div>
      ) : null}

      <div className="mt-7 grid grid-cols-[minmax(0,1fr)] gap-6 border-t border-slate-200 pt-6 lg:grid-cols-2">
        <section className="min-w-0" aria-labelledby="ai-context-heading">
          <h3 id="ai-context-heading" className="font-semibold text-slate-950">
            {t("contextManifest")}
          </h3>
          <p className="mt-1 text-xs [overflow-wrap:anywhere] break-words text-slate-500">
            {t("contextExcluded", {
              count: request.context_excluded_count,
              digest: request.context_digest,
            })}
          </p>
          <ul
            className="mt-3 max-h-80 space-y-2 overflow-y-auto pr-1 text-sm outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
            aria-label={t("contextAria")}
            tabIndex={0}
          >
            {request.context_manifest.map((entry, index) => (
              <li
                key={String(entry.reference_id ?? index)}
                className="min-w-0 rounded-lg bg-slate-50 p-3 text-slate-700"
              >
                <span className="font-mono text-xs break-all text-indigo-700">
                  {String(entry.reference_id ?? "context")}
                </span>
                <span className="mt-1 block [overflow-wrap:anywhere] break-words">
                  {String(
                    entry.summary ??
                      entry.relative_path ??
                      t("contextFallback"),
                  )}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="min-w-0" aria-labelledby="ai-eval-heading">
          <h3 id="ai-eval-heading" className="font-semibold text-slate-950">
            {t("evalEvidence")}
          </h3>
          <p className="mt-1 text-xs text-slate-500">{t("evalTrust")}</p>
          <ul className="mt-3 space-y-2 text-sm">
            {request.eval_results.map((result) => (
              <li
                key={result.id}
                className={`rounded-lg border p-3 ${
                  result.passed
                    ? "border-emerald-200 bg-emerald-50"
                    : "border-red-200 bg-red-50"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-semibold">
                    {localizeEval(result.eval_id, t)}{" "}
                    <code className="font-mono">({result.eval_id})</code>
                  </span>
                  <span className="text-xs font-semibold">
                    {result.passed ? t("pass") : t("fail")}
                  </span>
                </div>
                <p className="mt-1 leading-5">{result.summary}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="mt-7 grid gap-6 border-t border-slate-200 pt-6 lg:grid-cols-2">
        <section aria-labelledby="ai-trace-heading">
          <h3 id="ai-trace-heading" className="font-semibold text-slate-950">
            {t("providerTrace")}
          </h3>
          {request.traces.length ? (
            <ol className="mt-3 space-y-3">
              {request.traces.map((trace) => (
                <li
                  key={trace.id}
                  className="rounded-xl bg-slate-950 p-4 text-xs text-slate-100"
                >
                  <p className="font-semibold">
                    {t("traceAttempt", {
                      number: trace.attempt_number,
                      status: localizeStatus(trace.status, statusT),
                    })}
                  </p>
                  <p className="mt-2 leading-5 text-slate-300">
                    {t("traceUsage", {
                      latency: trace.latency_ms,
                      input: trace.input_tokens,
                      output: trace.output_tokens,
                      total: trace.total_tokens,
                    })}
                  </p>
                  <p className="mt-1 text-slate-400">
                    {t("traceCost", {
                      cost: trace.cost_estimate_microunits,
                      basis: trace.cost_basis,
                    })}
                  </p>
                  {trace.error_code ? (
                    <p className="mt-1 text-red-300">
                      {trace.error_category} · {trace.error_code}
                    </p>
                  ) : null}
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-3 text-sm text-slate-500">{t("noTrace")}</p>
          )}
        </section>

        <section aria-labelledby="ai-prompt-heading">
          <h3 id="ai-prompt-heading" className="font-semibold text-slate-950">
            {t("promptRecord")}
          </h3>
          <p className="mt-2 text-sm text-slate-600">
            {t("redactionSummary", {
              count: request.redaction_record.length,
            })}
          </p>
          <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
            <summary className="cursor-pointer text-sm font-semibold text-slate-800">
              {t("inspectPrompt")}
            </summary>
            <pre
              className="mt-3 max-h-80 overflow-auto text-xs whitespace-pre-wrap text-slate-700"
              tabIndex={0}
            >
              {JSON.stringify(
                {
                  prompt: request.prompt_payload,
                  request: request.request_payload,
                  redactions: request.redaction_record,
                },
                null,
                2,
              )}
            </pre>
          </details>
        </section>
      </div>

      {request.status === "generated" ? (
        <div className="mt-7 border-t border-slate-200 pt-6">
          <h3 className="font-semibold text-slate-950">{t("humanDecision")}</h3>
          <label
            className="mt-3 block text-sm font-semibold text-slate-700"
            htmlFor="ai-rejection-reason"
          >
            {t("rejectionReason")}
          </label>
          <textarea
            id="ai-rejection-reason"
            value={rejectionReason}
            onChange={(event) => setRejectionReason(event.target.value)}
            maxLength={2000}
            className="mt-1 min-h-24 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20"
            placeholder={t("rejectionPlaceholder")}
          />
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={() => void onDecision("approve")}
              className="rounded-xl bg-emerald-800 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              {t("approveHandoff")}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void reject()}
              className="rounded-xl bg-red-800 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              {t("rejectPlan")}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void onFreshness()}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              {t("revalidate")}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void onCancel()}
              className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-sm font-semibold text-amber-950 outline-none hover:bg-amber-100 focus-visible:ring-2 focus-visible:ring-amber-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              {t("cancelPlan")}
            </button>
          </div>
          {formError ? (
            <p className="mt-3 text-sm font-semibold text-red-700" role="alert">
              {formError}
            </p>
          ) : null}
        </div>
      ) : null}

      {request.status === "approved" && request.handoff_plan_id ? (
        <p className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
          {t("handoff", { id: request.handoff_plan_id })}
        </p>
      ) : null}
    </section>
  );
}
