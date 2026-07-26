"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  createPlan,
  createSnapshot,
  decidePlan,
  getRun,
  getSnapshot,
  listAuditEvents,
  listPlans,
  revisePlan,
  submitPlan,
  type AuditEvent,
  type Plan,
  type PlanRevisionInput,
  type Run,
  type Snapshot,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";

import { StatusPill } from "./status-pill";

type LoadState = "loading" | "ready" | "error";

function apiMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "出现未预期的错误，请安全重试。";
  }
  const prefix =
    error.status === 409 ? "状态冲突：页面数据可能已经发生变化。" : "";
  const request = error.requestId ? `（请求 ID：${error.requestId}）` : "";
  return `${prefix}${error.message}${request}`;
}

function stringValues(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function TextList({ title, items }: { title: string; items: string[] }) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">None recorded.</p>
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

function validationStepLabel(step: Plan["validation_steps"][number]): string {
  if (step.kind === "package_script") {
    return `Package script: ${step.workspace} · ${step.script}`;
  }
  if (step.kind === "make_target") {
    return `Make target: ${step.target}`;
  }
  if (step.kind === "browser_check") {
    return `Browser check: ${step.check} · ${step.viewport}`;
  }
  return `Repository status: ${step.expected}`;
}

function RunStepper({ status }: { status: Run["status"] }) {
  const steps = [
    {
      label: "Created",
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
      label: "Snapshot",
      active: [
        "snapshot_ready",
        "plan_ready",
        "awaiting_plan_approval",
        "approved",
        "rejected",
      ].includes(status),
    },
    {
      label: "Plan Draft",
      active: [
        "plan_ready",
        "awaiting_plan_approval",
        "approved",
        "rejected",
      ].includes(status),
    },
    {
      label: "Awaiting Approval",
      active: ["awaiting_plan_approval", "approved", "rejected"].includes(
        status,
      ),
    },
    {
      label:
        status === "approved"
          ? "Approved"
          : status === "rejected"
            ? "Rejected"
            : "Decision",
      active: ["approved", "rejected"].includes(status),
    },
  ];

  return (
    <ol className="grid gap-2 sm:grid-cols-5" aria-label="Run progress">
      {steps.map((step, index) => (
        <li
          key={step.label}
          className={`rounded-xl border p-3 text-sm ${
            step.active
              ? "border-blue-300 bg-blue-50 text-blue-950"
              : "border-slate-200 bg-slate-50 text-slate-500"
          }`}
        >
          <span className="block text-xs font-semibold">Step {index + 1}</span>
          <span className="mt-1 block">{step.label}</span>
        </li>
      ))}
    </ol>
  );
}

function RepositoryIntelligence({ snapshot }: { snapshot: Snapshot }) {
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
            Committed HEAD
          </p>
          <h2
            id="repository-intelligence-heading"
            className="mt-1 text-xl font-semibold text-slate-950"
          >
            Repository Intelligence
          </h2>
        </div>
        <StatusPill tone="positive">Immutable Snapshot</StatusPill>
      </div>

      {snapshot.repository_is_dirty ? (
        <div
          className="mt-5 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"
          role="status"
        >
          <p className="font-semibold">Dirty working tree detected</p>
          <p className="mt-1 leading-6">
            {snapshot.dirty_path_count} 个路径仅作为状态元数据记录；未读取 dirty
            或 untracked 内容。
          </p>
        </div>
      ) : null}

      <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
        {[
          ["HEAD", snapshot.source_revision],
          ["Branch", snapshot.branch_name],
          ["Fingerprint", snapshot.fingerprint],
          ["Package manager", snapshot.package_manager ?? "Not detected"],
          ["Tracked files", String(snapshot.tracked_file_count)],
          ["Selected files", String(snapshot.selected_file_count)],
          ["Skipped files", String(snapshot.skipped_file_count)],
          ["Selected bytes", String(snapshot.total_selected_bytes)],
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
        <TextList title="Frameworks" items={frameworks} />
        <TextList title="Languages" items={languages} />
        <TextList
          title="Test surfaces"
          items={snapshot.test_surfaces.map(
            (item) => `${String(item.kind)} · ${String(item.relative_path)}`,
          )}
        />
        <TextList
          title="Design-system signals"
          items={snapshot.design_system_signals.map(
            (item) => `${String(item.kind)} · ${String(item.relative_path)}`,
          )}
        />
        <TextList
          title="Repository instruction files"
          items={snapshot.repository_instructions.map(
            (item) =>
              `${String(item.relative_path)} · ${String(item.risk_label)}`,
          )}
        />
        <TextList
          title="Skipped sensitive files"
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
          title="Safety findings"
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
      setFormError("修订必须保留目标摘要和至少一个 scope 项。");
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
      setFormError("Reject 必须填写非空理由。");
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
            deterministic plan · v{plan.version}
          </p>
          <h2
            id="plan-review-heading"
            className="mt-1 text-xl font-semibold text-slate-950"
          >
            Plan Review
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
        <p className="font-semibold">Plan approval does not execute code.</p>
        <p className="mt-1">Execution is not available in Phase 2.</p>
      </div>

      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-semibold text-slate-500">Delivery package</dt>
          <dd className="mt-1 text-slate-900">{plan.delivery_package}</dd>
        </div>
        <div>
          <dt className="font-semibold text-slate-500">
            Required future permission
          </dt>
          <dd className="mt-1 text-slate-900">
            {plan.required_future_permission_level}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-semibold text-slate-500">Snapshot fingerprint</dt>
          <dd className="mt-1 font-mono text-xs break-all text-slate-900">
            {plan.snapshot_fingerprint}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-semibold text-slate-500">Objective</dt>
          <dd className="mt-1 leading-6 text-slate-900">
            {plan.objective_summary}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-semibold text-slate-500">Repository context</dt>
          <dd className="mt-1 leading-6 text-slate-900">
            {plan.repository_context_summary}
          </dd>
        </div>
      </dl>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <TextList title="Proposed scope" items={plan.proposed_change_scope} />
        <TextList title="Explicit non-goals" items={plan.explicit_non_goals} />
        <TextList title="Assumptions" items={plan.assumptions} />
        <TextList title="Risks" items={plan.risk_items} />
        <TextList
          title="Acceptance criteria"
          items={plan.acceptance_criteria}
        />
        <TextList
          title="Evidence requirements"
          items={plan.evidence_requirements}
        />
        <TextList title="Stop conditions" items={plan.stop_conditions} />
        <TextList
          title="Validation steps (display only)"
          items={plan.validation_steps.map(validationStepLabel)}
        />
      </div>

      {plan.status === "draft" && runStatus === "plan_ready" ? (
        <div className="mt-7 grid gap-6 border-t border-slate-200 pt-6 lg:grid-cols-2">
          <form onSubmit={(event) => void handleRevision(event)}>
            <h3 className="font-semibold text-slate-950">Create revision</h3>
            <label
              className="mt-3 block text-sm font-semibold text-slate-700"
              htmlFor="objective_summary"
            >
              Objective summary
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
              Scope, one item per line
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
              Create revision
            </button>
          </form>

          <div>
            <h3 className="font-semibold text-slate-950">
              Submit for approval
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              提交后当前版本冻结为 awaiting approval；过期版本会返回冲突。
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={() => void onSubmit()}
              className="mt-3 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              Submit latest Plan
            </button>
          </div>
        </div>
      ) : null}

      {plan.status === "awaiting_approval" &&
      runStatus === "awaiting_plan_approval" ? (
        <div className="mt-7 border-t border-slate-200 pt-6">
          <h3 className="font-semibold text-slate-950">Human decision</h3>
          <label
            className="mt-3 block text-sm font-semibold text-slate-700"
            htmlFor="rejection_reason"
          >
            Rejection reason
          </label>
          <textarea
            id="rejection_reason"
            value={rejectionReason}
            onChange={(event) => setRejectionReason(event.target.value)}
            maxLength={2000}
            className="mt-1 min-h-24 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
            placeholder="Required only when rejecting."
          />
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy}
              onClick={() => void onDecision("approve")}
              className="rounded-xl bg-emerald-800 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              Approve Plan
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void handleReject()}
              className="rounded-xl bg-red-800 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              Reject Plan
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
  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7"
      aria-labelledby="audit-heading"
    >
      <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
        Governance events
      </p>
      <h2
        id="audit-heading"
        className="mt-1 text-xl font-semibold text-slate-950"
      >
        Audit Timeline
      </h2>
      {events.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">No audit events yet.</p>
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
                  {formatTimestamp(event.created_at)}
                </time>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {event.actor_type} · request {event.request_id}
              </p>
              <pre
                aria-label={`${event.event_type} metadata`}
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
  const [run, setRun] = useState<Run | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [message, setMessage] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [deliveryPackage, setDeliveryPackage] = useState<
    Plan["delivery_package"]
  >("frontend_quality_remediation");

  const currentPlan = useMemo(() => plans[0] ?? null, [plans]);

  const load = useCallback(async () => {
    setState("loading");
    setMessage("");
    try {
      const loadedRun = await getRun(runId);
      const [loadedSnapshot, loadedPlans, loadedEvents] = await Promise.all([
        getSnapshot(runId).catch((error: unknown) => {
          if (error instanceof ApiError && error.status === 404) return null;
          throw error;
        }),
        listPlans(runId),
        listAuditEvents(runId),
      ]);
      setRun(loadedRun);
      setSnapshot(loadedSnapshot);
      setPlans(loadedPlans);
      setEvents(loadedEvents);
      setState("ready");
    } catch (error) {
      setMessage(apiMessage(error));
      setState("error");
    }
  }, [runId]);

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
      setActionMessage(apiMessage(error));
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
        返回 Task
      </Link>

      {state === "loading" ? (
        <div
          className="mt-6 rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-600"
          role="status"
        >
          Loading Run and Repository Intelligence…
        </div>
      ) : null}

      {state === "error" ? (
        <div
          className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <h1 className="text-lg font-semibold text-red-950">
            Unable to load Run
          </h1>
          <p className="mt-2 text-sm text-red-800">{message}</p>
          <button
            type="button"
            onClick={() => void load()}
            className="mt-4 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
          >
            Retry
          </button>
        </div>
      ) : null}

      {state === "ready" && run ? (
        <div className="mt-6 space-y-6">
          <header className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-xs font-semibold tracking-widest text-blue-700 uppercase">
                  Level 0 · Read-only · Committed HEAD
                </p>
                <h1 className="mt-2 text-2xl font-semibold text-slate-950 sm:text-3xl">
                  Governed Repository Investigation
                </h1>
                <p className="mt-2 font-mono text-xs break-all text-slate-500">
                  Run {run.id} · Trace {run.trace_id}
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
              Snapshot 只从已提交 Git 对象提取受限结构化事实。dirty 与 untracked
              内容不会被读取；仓库脚本不会执行。
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
                Repository Intelligence is empty
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                创建 Snapshot 会读取 allowlisted Git repository 的 committed
                HEAD，不会读取未提交文件内容。
              </p>
              {run.status === "created" ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void perform(() => createSnapshot(run.id))}
                  className="mt-4 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:opacity-60"
                >
                  {busy ? "Snapshotting…" : "Create committed-HEAD Snapshot"}
                </button>
              ) : null}
            </section>
          ) : (
            <RepositoryIntelligence snapshot={snapshot} />
          )}

          {snapshot && !currentPlan && run.status === "snapshot_ready" ? (
            <section className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6">
              <h2 className="text-lg font-semibold text-slate-950">
                Deterministic Plan is empty
              </h2>
              <p className="mt-2 text-sm text-slate-600">
                选择 V1 delivery package；生成器不会调用 LLM。
              </p>
              <label
                className="mt-4 block text-sm font-semibold text-slate-700"
                htmlFor="delivery-package"
              >
                Delivery package
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
                  Design Implementation
                </option>
                <option value="design_system_migration">
                  Design-System Migration
                </option>
                <option value="frontend_quality_remediation">
                  Frontend Quality Remediation
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
                Generate deterministic Plan
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
