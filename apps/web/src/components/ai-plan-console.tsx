"use client";

import { useState } from "react";

import type { AIPlanRequest } from "@/lib/api";

import { StatusPill } from "./status-pill";

function TextList({ title, items }: { title: string; items: string[] }) {
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
        <p className="mt-2 text-sm text-slate-500">None recorded.</p>
      )}
    </section>
  );
}

function operationLabel(
  operation: NonNullable<AIPlanRequest["plan"]>["proposed_operations"][number],
): string {
  if (operation.kind === "workspace_text_create_v1") {
    return `Create text · ${operation.relative_path} · ${operation.intent}`;
  }
  if (operation.kind === "workspace_text_replace_v1") {
    return `CAS replace text · ${operation.relative_path} · ${operation.intent}`;
  }
  return `Validation suite · ${operation.suite_id} v${operation.suite_version}`;
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
  const [rejectionReason, setRejectionReason] = useState("");
  const [formError, setFormError] = useState("");
  const plan = request.plan;

  async function reject() {
    const reason = rejectionReason.trim();
    if (!reason) {
      setFormError("Reject 必须填写非空理由。");
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
            Governed AI · deterministic fixture
          </p>
          <h2
            id="ai-plan-heading"
            className="mt-1 text-xl font-semibold text-slate-950"
          >
            Structured AI Plan
          </h2>
        </div>
        <StatusPill tone={statusTone(request.status)}>
          {request.status}
        </StatusPill>
      </div>

      <div className="mt-5 rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm leading-6 text-indigo-950">
        <p className="font-semibold">
          AI Plan approval does not execute code or issue authority.
        </p>
        <p className="mt-1">
          Execution Grant、Review Approval 与 Delivery Authorization
          仍需各自独立的人工决策。
        </p>
      </div>

      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        {[
          ["Provider", request.provider_id],
          [
            "Prompt",
            `${request.prompt_template_id} · ${request.prompt_version}`,
          ],
          [
            "Context",
            `${request.context_reference_count} refs · ${request.context_bytes} bytes`,
          ],
          ["Retries", String(request.retry_count)],
          ["Source revision", request.source_revision],
          ["Snapshot", request.snapshot_fingerprint],
          ["Prompt digest", request.prompt_digest],
          ["Request digest", request.request_digest],
          ["Plan digest", request.deterministic_digest ?? "Not available"],
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
          Provider capability metadata
        </h3>
        <dl className="mt-3 grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
          {[
            [
              "Implementation",
              request.provider_metadata.implementation_version,
            ],
            ["Model label", request.provider_metadata.model_label],
            [
              "Determinism / replay",
              `${request.provider_metadata.deterministic} / ${request.provider_metadata.fixture_replay}`,
            ],
            [
              "Structured output",
              String(request.provider_metadata.structured_output),
            ],
            [
              "Network access",
              String(request.provider_metadata.network_access),
            ],
            [
              "Credentials required",
              String(request.provider_metadata.credentials_required),
            ],
            ["Billing basis", request.provider_metadata.billing_basis],
            [
              "Context / output limits",
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
            Provider generation is in progress. The durable request can be
            safely refreshed or cancelled.
          </p>
          <button
            type="button"
            disabled={busy}
            onClick={() => void onCancel()}
            className="mt-3 rounded-xl border border-amber-300 bg-white px-4 py-2.5 text-sm font-semibold text-amber-950 outline-none hover:bg-amber-100 focus-visible:ring-2 focus-visible:ring-amber-700 focus-visible:ring-offset-2 disabled:opacity-60"
          >
            Cancel AI Plan generation
          </button>
        </div>
      ) : null}

      {request.error_message ? (
        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <p className="font-semibold">
            {request.error_code ?? "AI Plan failed"}
          </p>
          <p className="mt-1">{request.error_message}</p>
        </div>
      ) : null}

      {plan ? (
        <div className="mt-7 space-y-7">
          <section>
            <h3 className="text-sm font-semibold text-slate-500 uppercase">
              Requirement summary
            </h3>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-800">
              {plan.requirement_summary}
            </p>
          </section>

          <div className="grid gap-6 md:grid-cols-2">
            <TextList
              title="Repository findings"
              items={plan.repository_findings.map(
                (finding) =>
                  `${finding.kind}: ${finding.summary} [${finding.context_reference_ids.join(", ")}]`,
              )}
            />
            <TextList title="Assumptions" items={plan.assumptions} />
            <TextList
              title="Files and components expected to change"
              items={plan.expected_changes.map(
                (change) =>
                  `${change.change_type} ${change.relative_path} · ${change.component}: ${change.rationale}`,
              )}
            />
            <TextList
              title="Proposed typed operations"
              items={plan.proposed_operations.map(operationLabel)}
            />
            <TextList
              title="Validation suites"
              items={plan.validation_suites.map(
                (suite) =>
                  `${suite.suite_id}: ${suite.name} · ${suite.checks.length} required checks`,
              )}
            />
            <TextList
              title="Risks"
              items={plan.risks.map(
                (risk) =>
                  `${risk.severity} · ${risk.summary} Mitigation: ${risk.mitigation}`,
              )}
            />
            <TextList
              title="Acceptance criteria"
              items={plan.acceptance_criteria.map(
                (criterion) =>
                  `${criterion.statement} [${criterion.validation_suite_ids.join(", ")}]`,
              )}
            />
            <TextList
              title="Unresolved questions"
              items={plan.unresolved_questions}
            />
          </div>
        </div>
      ) : null}

      <div className="mt-7 grid gap-6 border-t border-slate-200 pt-6 lg:grid-cols-2">
        <section aria-labelledby="ai-context-heading">
          <h3 id="ai-context-heading" className="font-semibold text-slate-950">
            Input context manifest
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {request.context_excluded_count} entries excluded by policy/budget ·
            digest{" "}
            <span className="font-mono break-all">
              {request.context_digest}
            </span>
          </p>
          <ul
            className="mt-3 max-h-80 space-y-2 overflow-y-auto pr-1 text-sm outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
            aria-label="Bounded AI Plan input context manifest"
            tabIndex={0}
          >
            {request.context_manifest.map((entry, index) => (
              <li
                key={String(entry.reference_id ?? index)}
                className="rounded-lg bg-slate-50 p-3 text-slate-700"
              >
                <span className="font-mono text-xs text-indigo-700">
                  {String(entry.reference_id ?? "context")}
                </span>
                <span className="mt-1 block break-words">
                  {String(
                    entry.summary ??
                      entry.relative_path ??
                      "Structured context",
                  )}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="ai-eval-heading">
          <h3 id="ai-eval-heading" className="font-semibold text-slate-950">
            System-owned Eval evidence
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            Provider self-evaluation is not trusted or accepted.
          </p>
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
                  <span className="font-mono text-xs font-semibold">
                    {result.eval_id}
                  </span>
                  <span className="text-xs font-semibold">
                    {result.passed ? "PASS" : "FAIL"}
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
            Provider Trace
          </h3>
          {request.traces.length ? (
            <ol className="mt-3 space-y-3">
              {request.traces.map((trace) => (
                <li
                  key={trace.id}
                  className="rounded-xl bg-slate-950 p-4 text-xs text-slate-100"
                >
                  <p className="font-semibold">
                    Attempt {trace.attempt_number} · {trace.status}
                  </p>
                  <p className="mt-2 leading-5 text-slate-300">
                    {trace.latency_ms} ms · {trace.input_tokens} input ·{" "}
                    {trace.output_tokens} output · {trace.total_tokens} total
                  </p>
                  <p className="mt-1 text-slate-400">
                    Cost {trace.cost_estimate_microunits} micro-units ·{" "}
                    {trace.cost_basis}
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
            <p className="mt-3 text-sm text-slate-500">
              No Provider attempt recorded yet.
            </p>
          )}
        </section>

        <section aria-labelledby="ai-prompt-heading">
          <h3 id="ai-prompt-heading" className="font-semibold text-slate-950">
            Prompt and redaction record
          </h3>
          <p className="mt-2 text-sm text-slate-600">
            {request.redaction_record.length} redaction/classification records.
            Prompt data is bounded and contains no repository blob text.
          </p>
          <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
            <summary className="cursor-pointer text-sm font-semibold text-slate-800">
              Inspect persisted Prompt/request
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
          <h3 className="font-semibold text-slate-950">Human Plan decision</h3>
          <label
            className="mt-3 block text-sm font-semibold text-slate-700"
            htmlFor="ai-rejection-reason"
          >
            Rejection reason
          </label>
          <textarea
            id="ai-rejection-reason"
            value={rejectionReason}
            onChange={(event) => setRejectionReason(event.target.value)}
            maxLength={2000}
            className="mt-1 min-h-24 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20"
            placeholder="Required only when rejecting."
          />
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={() => void onDecision("approve")}
              className="rounded-xl bg-emerald-800 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              Approve AI Plan handoff
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void reject()}
              className="rounded-xl bg-red-800 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              Reject AI Plan
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void onFreshness()}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              Revalidate freshness
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void onCancel()}
              className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-sm font-semibold text-amber-950 outline-none hover:bg-amber-100 focus-visible:ring-2 focus-visible:ring-amber-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              Cancel AI Plan
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
          Human-approved handoff Plan:{" "}
          <span className="font-mono break-all">{request.handoff_plan_id}</span>
          . No Execution Grant or later approval was issued.
        </p>
      ) : null}
    </section>
  );
}
