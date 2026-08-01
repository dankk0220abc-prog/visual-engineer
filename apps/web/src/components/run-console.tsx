"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  cancelAIPlanRequest,
  createAIPlanRequest,
  createPlan,
  createSnapshot,
  decideAIPlanRequest,
  decidePlan,
  getRun,
  getSnapshot,
  listAuditEvents,
  listAIPlanRequests,
  listPlans,
  refreshAIPlanFreshness,
  revisePlan,
  submitPlan,
  type AIPlanRequest,
  type AuditEvent,
  type Plan,
  type PlanRevisionInput,
  type Run,
  type Snapshot,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { localizeApiError } from "@/lib/localization";

import { AIPlanConsole } from "./ai-plan-console";
import { StatusPill } from "./status-pill";

type LoadState = "loading" | "ready" | "error";

function stringValues(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function TextList({ title, items }: { title: string; items: string[] }) {
  const t = useTranslations("runConsole");
  return (
    <section>
      <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{t("noneRecorded")}</p>
      ) : (
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6 text-slate-700">
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function validationStepLabel(
  step: Plan["validation_steps"][number],
  t: ReturnType<typeof useTranslations>,
): string {
  if (step.kind === "package_script") {
    return t("packageScript", {
      workspace: step.workspace,
      script: step.script,
    });
  }
  if (step.kind === "make_target") {
    return t("makeTarget", { target: step.target });
  }
  if (step.kind === "browser_check") {
    return t("browserCheck", {
      check: step.check,
      viewport: step.viewport,
    });
  }
  return t("repositoryStatus", { expected: step.expected });
}

function RunStepper({ status }: { status: Run["status"] }) {
  const t = useTranslations("runConsole");
  const steps = [
    {
      label: t("stepCreated"),
      active: [
        "created",
        "snapshotting",
        "snapshot_ready",
        "plan_ready",
        "awaiting_plan_approval",
        "approved",
        "rejected",
      ].includes(status),
    },
    {
      label: t("stepSnapshot"),
      active: [
        "snapshot_ready",
        "plan_ready",
        "awaiting_plan_approval",
        "approved",
        "rejected",
      ].includes(status),
    },
    {
      label: t("stepPlanDraft"),
      active: [
        "plan_ready",
        "awaiting_plan_approval",
        "approved",
        "rejected",
      ].includes(status),
    },
    {
      label: t("stepAwaiting"),
      active: ["awaiting_plan_approval", "approved", "rejected"].includes(
        status,
      ),
    },
    {
      label:
        status === "approved"
          ? t("stepApproved")
          : status === "rejected"
            ? t("stepRejected")
            : t("stepDecision"),
      active: ["approved", "rejected"].includes(status),
    },
  ];

  return (
    <ol className="grid gap-2 sm:grid-cols-5" aria-label={t("progressLabel")}>
      {steps.map((step, index) => (
        <li
          key={step.label}
          className={`rounded-xl border p-3 text-sm ${
            step.active
              ? "border-blue-300 bg-blue-50 text-blue-950"
              : "border-slate-200 bg-slate-50 text-slate-500"
          }`}
        >
          <span className="block text-xs font-semibold">
            {t("step", { number: index + 1 })}
          </span>
          <span className="mt-1 block">{step.label}</span>
        </li>
      ))}
    </ol>
  );
}

function RepositoryIntelligence({ snapshot }: { snapshot: Snapshot }) {
  const t = useTranslations("runConsole");
  const frameworks = stringValues(snapshot.tech_stack.frameworks);
  const languages = stringValues(snapshot.tech_stack.languages);

  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7"
      aria-labelledby="repository-intelligence-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
            {t("committedHead")}
          </p>
          <h2
            id="repository-intelligence-heading"
            className="mt-1 text-xl font-semibold text-slate-950"
          >
            {t("repositoryIntelligence")}
          </h2>
        </div>
        <StatusPill tone="positive">{t("immutableSnapshot")}</StatusPill>
      </div>

      {snapshot.repository_is_dirty ? (
        <div
          className="mt-5 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"
          role="status"
        >
          <p className="font-semibold">{t("dirtyTitle")}</p>
          <p className="mt-1 leading-6">
            {t("dirtyDescription", { count: snapshot.dirty_path_count })}
          </p>
        </div>
      ) : null}

      <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
        {[
          [t("head"), snapshot.source_revision],
          [t("branch"), snapshot.branch_name],
          [t("fingerprint"), snapshot.fingerprint],
          [t("packageManager"), snapshot.package_manager ?? t("notDetected")],
          [t("trackedFiles"), String(snapshot.tracked_file_count)],
          [t("selectedFiles"), String(snapshot.selected_file_count)],
          [t("skippedFiles"), String(snapshot.skipped_file_count)],
          [t("selectedBytes"), String(snapshot.total_selected_bytes)],
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

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <TextList title={t("frameworks")} items={frameworks} />
        <TextList title={t("languages")} items={languages} />
        <TextList
          title={t("testSurfaces")}
          items={snapshot.test_surfaces.map(
            (item) => `${String(item.kind)} · ${String(item.relative_path)}`,
          )}
        />
        <TextList
          title={t("designSignals")}
          items={snapshot.design_system_signals.map(
            (item) => `${String(item.kind)} · ${String(item.relative_path)}`,
          )}
        />
        <TextList
          title={t("instructionFiles")}
          items={snapshot.repository_instructions.map(
            (item) =>
              `${String(item.relative_path)} · ${String(item.risk_label)}`,
          )}
        />
        <TextList
          title={t("skippedSensitive")}
          items={snapshot.safety_findings
            .filter((item) =>
              [
                "environment_file",
                "credential_file",
                "key_or_certificate_file",
              ].includes(String(item.rule_type)),
            )
            .map(
              (item) =>
                `${String(item.relative_path)} · ${String(item.rule_type)}`,
            )}
        />
      </div>

      <div className="mt-6">
        <TextList
          title={t("safetyFindings")}
          items={snapshot.safety_findings.map(
            (item) =>
              `${String(item.rule_type)}${
                item.relative_path ? ` · ${String(item.relative_path)}` : ""
              }: ${String(item.summary)}`,
          )}
        />
      </div>
    </section>
  );
}

function PlanReview({
  plan,
  runStatus,
  busy,
  onRevision,
  onSubmit,
  onDecision,
}: {
  plan: Plan;
  runStatus: Run["status"];
  busy: boolean;
  onRevision: (input: PlanRevisionInput) => Promise<void>;
  onSubmit: () => Promise<void>;
  onDecision: (
    decision: "approve" | "reject",
    comment?: string,
  ) => Promise<void>;
}) {
  const t = useTranslations("runConsole");
  const [rejectionReason, setRejectionReason] = useState("");
  const [formError, setFormError] = useState("");

  async function handleRevision(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    const data = new FormData(event.currentTarget);
    const objective = String(data.get("objective_summary") ?? "").trim();
    const scope = String(data.get("proposed_change_scope") ?? "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    if (!objective || scope.length === 0) {
      setFormError(t("revisionValidation"));
      return;
    }
    await onRevision({
      objective_summary: objective,
      proposed_change_scope: scope,
    });
  }

  async function handleReject() {
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
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7"
      aria-labelledby="plan-review-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold tracking-widest text-violet-700 uppercase">
            {plan.source === "governed_ai"
              ? t("aiHandoffVersion", { version: plan.version })
              : t("deterministicVersion", { version: plan.version })}
          </p>
          <h2
            id="plan-review-heading"
            className="mt-1 text-xl font-semibold text-slate-950"
          >
            {t("planReview")}
          </h2>
        </div>
        <StatusPill
          tone={
            plan.status === "approved"
              ? "positive"
              : plan.status === "rejected"
                ? "negative"
                : "pending"
          }
        >
          {plan.status}
        </StatusPill>
      </div>

      <div className="mt-5 rounded-xl border border-violet-200 bg-violet-50 p-4 text-sm text-violet-950">
        <p className="font-semibold">{t("approvalBoundary")}</p>
        <p className="mt-1">
          {plan.source === "governed_ai"
            ? t("aiAuthorityHelp")
            : t("phase2AuthorityHelp")}
        </p>
      </div>

      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-semibold text-slate-500">
            {t("deliveryPackage")}
          </dt>
          <dd className="mt-1 text-slate-900">{plan.delivery_package}</dd>
        </div>
        <div>
          <dt className="font-semibold text-slate-500">
            {t("futurePermission")}
          </dt>
          <dd className="mt-1 text-slate-900">
            {plan.required_future_permission_level}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-semibold text-slate-500">
            {t("snapshotFingerprint")}
          </dt>
          <dd className="mt-1 font-mono text-xs break-all text-slate-900">
            {plan.snapshot_fingerprint}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-semibold text-slate-500">{t("objective")}</dt>
          <dd className="mt-1 leading-6 text-slate-900">
            {plan.objective_summary}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-semibold text-slate-500">
            {t("repositoryContext")}
          </dt>
          <dd className="mt-1 leading-6 text-slate-900">
            {plan.repository_context_summary}
          </dd>
        </div>
      </dl>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <TextList
          title={t("proposedScope")}
          items={plan.proposed_change_scope}
        />
        <TextList title={t("nonGoals")} items={plan.explicit_non_goals} />
        <TextList title={t("assumptions")} items={plan.assumptions} />
        <TextList title={t("risks")} items={plan.risk_items} />
        <TextList
          title={t("acceptanceCriteria")}
          items={plan.acceptance_criteria}
        />
        <TextList
          title={t("evidenceRequirements")}
          items={plan.evidence_requirements}
        />
        <TextList title={t("stopConditions")} items={plan.stop_conditions} />
        <TextList
          title={t("validationSteps")}
          items={plan.validation_steps.map((step) =>
            validationStepLabel(step, t),
          )}
        />
      </div>

      {plan.status === "draft" && runStatus === "plan_ready" ? (
        <div className="mt-7 grid gap-6 border-t border-slate-200 pt-6 lg:grid-cols-2">
          <form onSubmit={(event) => void handleRevision(event)}>
            <h3 className="font-semibold text-slate-950">
              {t("createRevision")}
            </h3>
            <label
              className="mt-3 block text-sm font-semibold text-slate-700"
              htmlFor="objective_summary"
            >
              {t("objectiveSummary")}
            </label>
            <textarea
              id="objective_summary"
              name="objective_summary"
              defaultValue={plan.objective_summary}
              maxLength={4000}
              className="mt-1 min-h-24 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
            />
            <label
              className="mt-3 block text-sm font-semibold text-slate-700"
              htmlFor="proposed_change_scope"
            >
              {t("scopeLines")}
            </label>
            <textarea
              id="proposed_change_scope"
              name="proposed_change_scope"
              defaultValue={plan.proposed_change_scope.join("\n")}
              className="mt-1 min-h-32 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
            />
            <button
              type="submit"
              disabled={busy}
              className="mt-3 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              {t("createRevision")}
            </button>
          </form>

          <div>
            <h3 className="font-semibold text-slate-950">{t("submitTitle")}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {t("submitHelp")}
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={() => void onSubmit()}
              className="mt-3 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              {t("submitLatest")}
            </button>
          </div>
        </div>
      ) : null}

      {plan.status === "awaiting_approval" &&
      runStatus === "awaiting_plan_approval" ? (
        <div className="mt-7 border-t border-slate-200 pt-6">
          <h3 className="font-semibold text-slate-950">{t("humanDecision")}</h3>
          <label
            className="mt-3 block text-sm font-semibold text-slate-700"
            htmlFor="rejection_reason"
          >
            {t("rejectionReason")}
          </label>
          <textarea
            id="rejection_reason"
            value={rejectionReason}
            onChange={(event) => setRejectionReason(event.target.value)}
            maxLength={2000}
            className="mt-1 min-h-24 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
            placeholder={t("rejectionPlaceholder")}
          />
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={() => void onDecision("approve")}
              className="rounded-xl bg-emerald-800 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              {t("approvePlan")}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void handleReject()}
              className="rounded-xl bg-red-800 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              {t("rejectPlan")}
            </button>
          </div>
        </div>
      ) : null}

      {formError ? (
        <p className="mt-4 text-sm font-semibold text-red-700" role="alert">
          {formError}
        </p>
      ) : null}
    </section>
  );
}

function AuditTimeline({ events }: { events: AuditEvent[] }) {
  const locale = useLocale();
  const t = useTranslations("runConsole");
  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7"
      aria-labelledby="audit-heading"
    >
      <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
        {t("auditEyebrow")}
      </p>
      <h2
        id="audit-heading"
        className="mt-1 text-xl font-semibold text-slate-950"
      >
        {t("auditTimeline")}
      </h2>
      {events.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">{t("noAudit")}</p>
      ) : (
        <ol className="mt-5 space-y-4 border-l border-slate-200 pl-5">
          {events.map((event) => (
            <li key={event.id} className="relative">
              <span className="absolute top-1.5 -left-[1.45rem] h-2.5 w-2.5 rounded-full bg-blue-600" />
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-sm font-semibold text-slate-950">
                  {event.event_type}
                </h3>
                <time
                  className="text-xs text-slate-500"
                  dateTime={event.created_at}
                >
                  {formatTimestamp(event.created_at, locale)}
                </time>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {t("auditActor", {
                  actor: event.actor_type,
                  requestId: event.request_id,
                })}
              </p>
              <pre
                aria-label={t("auditMetadata", { type: event.event_type })}
                className="mt-2 overflow-x-auto rounded-lg bg-slate-50 p-2 text-xs whitespace-pre-wrap text-slate-700"
                tabIndex={0}
              >
                {JSON.stringify(event.metadata, null, 2)}
              </pre>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export function RunConsole({ runId }: { runId: string }) {
  const t = useTranslations("runConsole");
  const commonT = useTranslations("common");
  const errorT = useTranslations("errors");
  const [run, setRun] = useState<Run | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [aiPlanRequests, setAIPlanRequests] = useState<AIPlanRequest[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [message, setMessage] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [deliveryPackage, setDeliveryPackage] = useState<
    Plan["delivery_package"]
  >("frontend_quality_remediation");

  const currentPlan = useMemo(() => plans[0] ?? null, [plans]);
  const currentAIPlan = useMemo(
    () => aiPlanRequests[0] ?? null,
    [aiPlanRequests],
  );

  const load = useCallback(async () => {
    setState("loading");
    setMessage("");
    try {
      const loadedRun = await getRun(runId);
      const [loadedSnapshot, loadedPlans, loadedAIPlans, loadedEvents] =
        await Promise.all([
          getSnapshot(runId).catch((error: unknown) => {
            if (error instanceof ApiError && error.status === 404) return null;
            throw error;
          }),
          listPlans(runId),
          listAIPlanRequests(runId),
          listAuditEvents(runId),
        ]);
      setRun(loadedRun);
      setSnapshot(loadedSnapshot);
      setPlans(loadedPlans);
      setAIPlanRequests(loadedAIPlans);
      setEvents(loadedEvents);
      setState("ready");
    } catch (error) {
      setMessage(localizeApiError(error, errorT));
      setState("error");
    }
  }, [errorT, runId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function perform(action: () => Promise<unknown>) {
    setBusy(true);
    setActionMessage("");
    try {
      await action();
      await load();
    } catch (error) {
      setActionMessage(localizeApiError(error, errorT));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <Link
        className="inline-flex rounded-lg px-2 py-1 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
        href={run ? `/tasks/${run.task_id}` : "/"}
      >
        <span aria-hidden="true">←&nbsp;</span>
        {t("back")}
      </Link>

      {state === "loading" ? (
        <div
          className="mt-6 rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-600"
          role="status"
        >
          {t("loading")}
        </div>
      ) : null}

      {state === "error" ? (
        <div
          className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <h1 className="text-lg font-semibold text-red-950">
            {t("loadFailed")}
          </h1>
          <p className="mt-2 text-sm text-red-800">{message}</p>
          <button
            type="button"
            onClick={() => void load()}
            className="mt-4 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
          >
            {commonT("actions.retry")}
          </button>
        </div>
      ) : null}

      {state === "ready" && run ? (
        <div className="mt-6 space-y-6">
          <header className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
                  {t("headerEyebrow")}
                </p>
                <h1 className="mt-2 text-2xl font-semibold text-slate-950 sm:text-3xl">
                  {t("title")}
                </h1>
                <p className="mt-2 font-mono text-xs break-all text-slate-500">
                  {t("runTrace", { runId: run.id, traceId: run.trace_id })}
                </p>
              </div>
              <StatusPill
                tone={
                  run.status === "approved"
                    ? "positive"
                    : run.status === "rejected" || run.status === "failed"
                      ? "negative"
                      : "pending"
                }
              >
                {run.status}
              </StatusPill>
            </div>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-600">
              {t("description")}
            </p>
            <div className="mt-6">
              <RunStepper status={run.status} />
            </div>
          </header>

          {actionMessage ? (
            <div
              className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
              role="alert"
            >
              {actionMessage}
            </div>
          ) : null}

          {!snapshot ? (
            <section className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6">
              <h2 className="text-lg font-semibold text-slate-950">
                {t("emptyIntelligence")}
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {t("emptyIntelligenceHelp")}
              </p>
              {run.status === "created" ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void perform(() => createSnapshot(run.id))}
                  className="mt-4 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:opacity-60"
                >
                  {busy ? t("snapshotting") : t("createSnapshot")}
                </button>
              ) : null}
            </section>
          ) : (
            <RepositoryIntelligence snapshot={snapshot} />
          )}

          {snapshot &&
          !currentPlan &&
          !currentAIPlan &&
          run.status === "snapshot_ready" ? (
            <section className="rounded-2xl border border-indigo-300 bg-gradient-to-br from-indigo-50 to-white p-6 shadow-sm">
              <p className="text-xs font-semibold tracking-widest text-indigo-700 uppercase">
                {t("firstSlice")}
              </p>
              <h2 className="mt-1 text-lg font-semibold text-slate-950">
                {t("emptyAiPlan")}
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                {t("aiPlanHelp")}
              </p>
              <p className="mt-2 max-w-3xl rounded-lg border border-indigo-200 bg-white/80 p-3 text-sm leading-6 text-indigo-950">
                {t("interfaceOutputBoundary")}
              </p>
              <label
                className="mt-4 block text-sm font-semibold text-slate-700"
                htmlFor="ai-delivery-package"
              >
                {t("aiDeliveryPackage")}
              </label>
              <select
                id="ai-delivery-package"
                value={deliveryPackage}
                onChange={(event) =>
                  setDeliveryPackage(
                    event.target.value as Plan["delivery_package"],
                  )
                }
                className="mt-1 w-full max-w-md rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20"
              >
                <option value="design_implementation">
                  {t("designImplementation")}
                </option>
                <option value="design_system_migration">
                  {t("designSystemMigration")}
                </option>
                <option value="frontend_quality_remediation">
                  {t("frontendQualityRemediation")}
                </option>
              </select>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  void perform(() =>
                    createAIPlanRequest(
                      run.id,
                      { delivery_package: deliveryPackage },
                      crypto.randomUUID(),
                    ),
                  )
                }
                className="mt-4 block rounded-xl bg-indigo-800 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2 disabled:opacity-60"
              >
                {busy ? t("generatingAi") : t("generateAi")}
              </button>
            </section>
          ) : null}

          {currentAIPlan ? (
            <AIPlanConsole
              key={`${currentAIPlan.id}-${currentAIPlan.status}`}
              request={currentAIPlan}
              busy={busy}
              onFreshness={() =>
                perform(() => refreshAIPlanFreshness(currentAIPlan.id))
              }
              onCancel={() =>
                perform(() => cancelAIPlanRequest(currentAIPlan.id))
              }
              onDecision={(decision, comment) =>
                perform(() =>
                  decideAIPlanRequest(currentAIPlan.id, {
                    decision,
                    comment,
                  }),
                )
              }
            />
          ) : null}

          {snapshot &&
          !currentPlan &&
          !currentAIPlan &&
          run.status === "snapshot_ready" ? (
            <section className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6">
              <h2 className="text-lg font-semibold text-slate-950">
                {t("emptyPlan")}
              </h2>
              <p className="mt-2 text-sm text-slate-600">{t("planHelp")}</p>
              <label
                className="mt-4 block text-sm font-semibold text-slate-700"
                htmlFor="delivery-package"
              >
                {t("deliveryPackage")}
              </label>
              <select
                id="delivery-package"
                value={deliveryPackage}
                onChange={(event) =>
                  setDeliveryPackage(
                    event.target.value as Plan["delivery_package"],
                  )
                }
                className="mt-1 w-full max-w-md rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
              >
                <option value="design_implementation">
                  {t("designImplementation")}
                </option>
                <option value="design_system_migration">
                  {t("designSystemMigration")}
                </option>
                <option value="frontend_quality_remediation">
                  {t("frontendQualityRemediation")}
                </option>
              </select>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  void perform(() =>
                    createPlan(run.id, {
                      delivery_package: deliveryPackage,
                    }),
                  )
                }
                className="mt-4 block rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:opacity-60"
              >
                {t("generatePlan")}
              </button>
            </section>
          ) : null}

          {currentPlan ? (
            <PlanReview
              key={`${currentPlan.id}-${currentPlan.status}`}
              plan={currentPlan}
              runStatus={run.status}
              busy={busy}
              onRevision={(input) =>
                perform(() => revisePlan(run.id, currentPlan.version, input))
              }
              onSubmit={() =>
                perform(() => submitPlan(run.id, currentPlan.version))
              }
              onDecision={(decision, comment) =>
                perform(() =>
                  decidePlan(run.id, currentPlan.version, {
                    decision,
                    comment,
                  }),
                )
              }
            />
          ) : null}

          <AuditTimeline events={events} />
        </div>
      ) : null}
    </main>
  );
}
