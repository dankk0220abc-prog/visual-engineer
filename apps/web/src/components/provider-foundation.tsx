"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  connectAIProviderCredential,
  disconnectAIProviderCredential,
  getLiveProviderEvidence,
  listAIProviders,
  listLiveProviderEvidence,
  type AIProvider,
  type CreateAIPlanRequestInput,
  type LiveProviderEvidenceDetail,
  type LiveProviderEvidenceSummary,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { localizeStatus } from "@/lib/localization";

import { StatusPill } from "./status-pill";
import { TechnicalValue } from "./technical-value";

const capabilityKeys = [
  "structured_output",
  "tool_calling",
  "streaming",
  "reasoning",
  "token_usage_reporting",
  "request_id",
  "configurable_timeout",
  "model_availability",
  "maximum_output_control",
] as const satisfies ReadonlyArray<keyof AIProvider["capabilities"]>;

function isRealProvider(provider: AIProvider): boolean {
  return provider.provider_id !== "deterministic-fixture";
}

function useProviderLabels() {
  const t = useTranslations("providerFoundation");
  return {
    providerName: {
      "deterministic-fixture": t("providerName.deterministicFixture"),
      zhipu: t("providerName.zhipu"),
      qwen: t("providerName.qwen"),
      deepseek: t("providerName.deepseek"),
      doubao: t("providerName.doubao"),
      kimi: t("providerName.kimi"),
    },
    reason: {
      available: t("reason.available"),
      missing_session_credential: t("reason.missing_session_credential"),
      connected_with_user_credential: t(
        "reason.connected_with_user_credential",
      ),
      live_validation_not_performed: t("reason.live_validation_not_performed"),
    },
    capability: {
      structured_output: t("capability.structured_output"),
      tool_calling: t("capability.tool_calling"),
      streaming: t("capability.streaming"),
      reasoning: t("capability.reasoning"),
      token_usage_reporting: t("capability.token_usage_reporting"),
      request_id: t("capability.request_id"),
      configurable_timeout: t("capability.configurable_timeout"),
      model_availability: t("capability.model_availability"),
      maximum_output_control: t("capability.maximum_output_control"),
    },
    support: {
      supported: t("support.supported"),
      unsupported: t("support.unsupported"),
      not_verified: t("support.not_verified"),
    },
  };
}

function technicalErrorCode(error: unknown): string {
  return error instanceof ApiError ? error.code : "unexpected_error";
}

function ErrorNotice({
  title,
  action,
  code,
}: {
  title: string;
  action: string;
  code: string;
}) {
  const t = useTranslations("providerFoundation");
  return (
    <div
      className="rounded-xl border border-red-200 bg-red-50 p-4"
      role="alert"
    >
      <p className="font-semibold text-red-950">{title}</p>
      <p className="mt-1 text-sm leading-6 text-red-800">{action}</p>
      <details className="mt-2 text-xs text-red-800">
        <summary className="cursor-pointer font-semibold outline-none focus-visible:ring-2 focus-visible:ring-red-700">
          {t("technicalDetails")}
        </summary>
        <code className="mt-2 block font-mono break-all">{code}</code>
      </details>
    </div>
  );
}

function ProviderIdentity({ provider }: { provider: AIProvider }) {
  const t = useTranslations("providerFoundation");
  const labels = useProviderLabels();
  const connected = provider.session_credential_status === "connected";
  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="min-w-0 text-base font-semibold break-words text-slate-950">
          {labels.providerName[provider.provider_id]}
        </h3>
        <StatusPill
          tone={
            provider.provider_id === "deterministic-fixture" || connected
              ? "positive"
              : "pending"
          }
        >
          {provider.provider_id === "deterministic-fixture"
            ? t("fixtureDefaultShort")
            : connected
              ? t("sessionConnected")
              : t("sessionNotConnected")}
        </StatusPill>
      </div>
      <p className="mt-1 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-600">
        <code className="font-mono break-all text-slate-800">
          {provider.provider_id}
        </code>
        <span aria-hidden="true">·</span>
        <span className="break-all">{provider.model_id}</span>
      </p>
    </div>
  );
}

function ProviderState({ provider }: { provider: AIProvider }) {
  const t = useTranslations("providerFoundation");
  return (
    <dl className="grid gap-x-5 gap-y-3 text-sm sm:grid-cols-3">
      <div>
        <dt className="font-semibold text-slate-500">{t("currentSession")}</dt>
        <dd className="mt-1 text-slate-900">
          {provider.session_credential_status === "not_required"
            ? t("credentialNotRequired")
            : provider.session_credential_status === "connected"
              ? t("usingYourCredential")
              : t("sessionNotConnected")}
        </dd>
      </div>
      <div>
        <dt className="font-semibold text-slate-500">{t("adapter")}</dt>
        <dd className="mt-1 text-slate-900">{t("adapterSupported")}</dd>
      </div>
      <div>
        <dt className="font-semibold text-slate-500">{t("realValidation")}</dt>
        <dd className="mt-1 text-slate-900">
          {provider.live_validation_status === "live_verified"
            ? t("liveVerified")
            : provider.live_validation_status === "fixture_validated"
              ? t("fixtureValidated")
              : t("liveNotPerformed")}
        </dd>
      </div>
    </dl>
  );
}

function ProviderRegistryList({
  providers,
  onConfigure,
  onDisconnect,
  disconnecting,
}: {
  providers: AIProvider[];
  onConfigure: (provider: AIProvider) => void;
  onDisconnect: (provider: AIProvider) => void;
  disconnecting: string;
}) {
  const t = useTranslations("providerFoundation");
  const labels = useProviderLabels();
  return (
    <section aria-labelledby="provider-registry-heading">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2
            id="provider-registry-heading"
            className="text-xl font-semibold text-slate-950"
          >
            {t("registryTitle")}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {t("registryDescription")}
          </p>
        </div>
        <p className="text-sm font-semibold text-slate-700">
          {t("providerCount", { count: providers.length })}
        </p>
      </div>

      <ul className="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {providers.map((provider) => (
          <li
            key={provider.provider_id}
            className="grid gap-5 border-b border-slate-200 p-5 last:border-b-0 lg:grid-cols-[minmax(13rem,0.7fr)_minmax(0,1fr)] lg:p-6"
          >
            <div className="min-w-0">
              <ProviderIdentity provider={provider} />
              <p
                id={`provider-${provider.provider_id}-reason`}
                className={`mt-3 text-sm leading-6 ${provider.enabled ? "text-emerald-800" : "text-amber-900"}`}
              >
                {labels.reason[provider.status_reason]}
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {provider.provider_id === "deterministic-fixture"
                  ? t("fixtureDescription")
                  : t("adapterDescription")}
              </p>
              {isRealProvider(provider) ? (
                provider.session_credential_status === "connected" ? (
                  <button
                    type="button"
                    className="mt-4 rounded-lg px-3 py-2 text-sm font-semibold text-red-700 ring-1 ring-red-200 outline-none hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={disconnecting === provider.provider_id}
                    onClick={() => onDisconnect(provider)}
                  >
                    {disconnecting === provider.provider_id
                      ? t("disconnecting")
                      : t("disconnect")}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="mt-4 rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                    onClick={() => onConfigure(provider)}
                  >
                    {t("configureOwnKey")}
                  </button>
                )
              ) : null}
              <a
                className="mt-4 ml-3 inline-flex rounded-md text-sm font-semibold text-blue-700 outline-none hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                href={provider.documentation_url}
                rel="noreferrer"
                target="_blank"
              >
                {t("officialDocumentation")}
              </a>
            </div>

            <div className="min-w-0">
              <ProviderState provider={provider} />
              <div className="mt-5">
                <h4 className="text-sm font-semibold text-slate-950">
                  {t("capabilities")}
                </h4>
                <dl className="mt-2 grid gap-x-5 gap-y-2 text-xs sm:grid-cols-2 xl:grid-cols-3">
                  {capabilityKeys.map((key) => (
                    <div
                      key={key}
                      className="flex min-w-0 items-baseline justify-between gap-3 border-b border-slate-100 py-1.5"
                    >
                      <dt className="min-w-0 break-words text-slate-600">
                        {labels.capability[key]}
                      </dt>
                      <dd className="shrink-0 font-semibold text-slate-900">
                        {labels.support[provider.capabilities[key]]}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function CredentialDialog({
  providers,
  initialProvider,
  onClose,
  onConnected,
}: {
  providers: AIProvider[];
  initialProvider: AIProvider | null;
  onClose: () => void;
  onConnected: () => Promise<void>;
}) {
  const t = useTranslations("providerFoundation");
  const labels = useProviderLabels();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [providerId, setProviderId] =
    useState<AIProvider["provider_id"]>("zhipu");
  const [secret, setSecret] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorCode, setErrorCode] = useState("");

  useEffect(() => {
    const dialog = dialogRef.current;
    if (initialProvider) {
      queueMicrotask(() => {
        setProviderId(initialProvider.provider_id);
        setSecret("");
        setErrorCode("");
      });
      if (dialog && !dialog.open) {
        if (typeof dialog.showModal === "function") dialog.showModal();
        else dialog.setAttribute("open", "");
      }
    } else if (dialog?.open) {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    }
  }, [initialProvider]);

  async function connect(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setErrorCode("");
    try {
      await connectAIProviderCredential(providerId, secret);
      setSecret("");
      await onConnected();
      onClose();
    } catch (error) {
      setErrorCode(technicalErrorCode(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="byok-dialog-title"
      className="m-auto w-[min(34rem,calc(100%-2rem))] rounded-2xl border border-slate-200 bg-white p-0 text-slate-950 shadow-xl backdrop:bg-slate-950/45"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClose={onClose}
    >
      <form className="p-5 sm:p-6" onSubmit={(event) => void connect(event)}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="byok-dialog-title" className="text-xl font-semibold">
              {t("dialogTitle")}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {t("dialogDescription")}
            </p>
          </div>
          <button
            type="button"
            className="rounded-lg px-2 py-1 text-sm font-semibold text-slate-600 outline-none hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-blue-600"
            onClick={onClose}
          >
            {t("closeDialog")}
          </button>
        </div>

        <div className="mt-5 space-y-4">
          <div>
            <label className="text-sm font-semibold" htmlFor="byok-provider">
              {t("providerField")}
            </label>
            <select
              id="byok-provider"
              className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
              value={providerId}
              onChange={(event) =>
                setProviderId(
                  event.currentTarget.value as AIProvider["provider_id"],
                )
              }
            >
              {providers.filter(isRealProvider).map((provider) => (
                <option key={provider.provider_id} value={provider.provider_id}>
                  {labels.providerName[provider.provider_id]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-semibold" htmlFor="byok-secret">
              {t("secretField")}
            </label>
            <input
              autoFocus
              autoComplete="off"
              id="byok-secret"
              name="api-key"
              type="password"
              minLength={8}
              maxLength={512}
              required
              value={secret}
              onChange={(event) => setSecret(event.currentTarget.value)}
              aria-describedby="byok-handling"
              className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm outline-none placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20"
              placeholder={t("secretPlaceholder")}
            />
          </div>
          <p
            id="byok-handling"
            className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm leading-6 text-blue-950"
          >
            {t("credentialHandling")}
          </p>
          {errorCode ? (
            <ErrorNotice
              title={t("connectFailed")}
              action={t("connectFailedAction")}
              code={errorCode}
            />
          ) : null}
        </div>

        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            className="min-h-11 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-700 ring-1 ring-slate-300 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
            onClick={onClose}
          >
            {t("cancel")}
          </button>
          <button
            type="submit"
            disabled={submitting || secret.length < 8}
            className="min-h-11 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? t("connecting") : t("connect")}
          </button>
        </div>
      </form>
    </dialog>
  );
}

function EvidenceDetail({
  evidence,
}: {
  evidence: LiveProviderEvidenceDetail;
}) {
  const locale = useLocale();
  const evidenceT = useTranslations("liveEvidence");
  const statusT = useTranslations("common.status");
  const seconds = (evidence.client_total_elapsed_ms ?? 0) / 1000;
  const governanceStatus: Record<string, string> = {
    generated: evidenceT("governance.generated"),
    not_decided: evidenceT("governance.not_decided"),
    approved: evidenceT("governance.approved"),
    rejected: evidenceT("governance.rejected"),
    not_issued: evidenceT("governance.not_issued"),
    present: evidenceT("governance.present"),
    none: evidenceT("governance.none"),
    not_granted: evidenceT("governance.not_granted"),
    not_created: evidenceT("governance.not_created"),
    not_authorized: evidenceT("governance.not_authorized"),
  };
  return (
    <article className="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-200 p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-xl font-semibold text-slate-950">
                {evidenceT("detailTitle")}
              </h3>
              <StatusPill tone="positive">LIVE</StatusPill>
              <StatusPill tone="positive">
                {localizeStatus(evidence.lifecycle, statusT)}
              </StatusPill>
            </div>
            <p className="mt-2 text-sm text-slate-600">
              {evidenceT("completedAt", {
                value: formatTimestamp(evidence.completed_at, locale),
              })}
            </p>
          </div>
          <TechnicalValue value={evidence.correlation} visible={12} />
        </div>
      </header>

      <section
        id="live-evidence-plan"
        data-testid="live-evidence-plan"
        className="border-b border-slate-200 p-5 sm:p-6"
        aria-labelledby="live-plan-heading"
      >
        <h4
          id="live-plan-heading"
          className="text-lg font-semibold text-slate-950"
        >
          {evidenceT("planTitle")}
        </h4>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
          {evidence.plan_summary}
        </p>
        <ol className="mt-4 grid gap-3 md:grid-cols-2">
          {evidence.operations.map((operation, index) => (
            <li
              key={`${operation.kind}-${index}`}
              className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-4"
            >
              <p className="text-xs font-semibold text-slate-500">
                {evidenceT("step", { number: index + 1 })}
              </p>
              <code className="mt-1 block font-mono text-xs break-all text-slate-800">
                {operation.kind}
              </code>
              {operation.target ? (
                <p className="mt-2 text-sm break-all text-slate-700">
                  {operation.target}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
        <div className="mt-5">
          <h5 className="text-sm font-semibold text-slate-950">
            {evidenceT("policyEvaluation")}
          </h5>
          <ul className="mt-2 space-y-2">
            {evidence.evaluations.map((evaluation) => (
              <li
                key={evaluation.eval_id}
                className="flex min-w-0 items-start justify-between gap-3 rounded-lg border border-slate-100 px-3 py-2"
              >
                <div className="min-w-0">
                  <code className="font-mono text-xs break-all text-slate-600">
                    {evaluation.eval_id}
                  </code>
                  <p className="mt-1 text-sm leading-5 text-slate-700">
                    {evaluation.summary}
                  </p>
                </div>
                <StatusPill tone={evaluation.passed ? "positive" : "negative"}>
                  {evaluation.passed
                    ? evidenceT("passed")
                    : evidenceT("failed")}
                </StatusPill>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section
        id="live-evidence-audit"
        data-testid="live-evidence-audit"
        className="border-b border-slate-200 p-5 sm:p-6"
        aria-labelledby="live-audit-heading"
      >
        <h4
          id="live-audit-heading"
          className="text-lg font-semibold text-slate-950"
        >
          {evidenceT("auditTitle")}
        </h4>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="font-semibold text-slate-500">
              {evidenceT("provider")}
            </dt>
            <dd className="mt-1 text-slate-900">Zhipu GLM</dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-500">
              {evidenceT("model")}
            </dt>
            <dd className="mt-1 text-slate-900">
              {evidence.effective_model_id ?? evidence.requested_model_id}
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-500">
              {evidenceT("usage")}
            </dt>
            <dd className="mt-1 text-slate-900">
              {evidenceT("usageValue", {
                input: evidence.input_tokens ?? evidenceT("unknown"),
                output: evidence.output_tokens ?? evidenceT("unknown"),
                total: evidence.total_tokens ?? evidenceT("unknown"),
              })}
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-500">
              {evidenceT("latency")}
            </dt>
            <dd className="mt-1 text-slate-900">
              {evidenceT("seconds", { value: seconds.toFixed(2) })}
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-500">
              {evidenceT("billing")}
            </dt>
            <dd className="mt-1 text-slate-900">
              {evidenceT("billingUnknown")}
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-500">
              {evidenceT("upstream")}
            </dt>
            <dd className="mt-1 text-slate-900">
              {evidenceT("fingerprintOnly")}
            </dd>
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <dt className="font-semibold text-slate-500">
              {evidenceT("requestDigest")}
            </dt>
            <dd className="mt-1">
              <TechnicalValue value={evidence.request_digest} />
            </dd>
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <dt className="font-semibold text-slate-500">
              {evidenceT("responseDigest")}
            </dt>
            <dd className="mt-1">
              <TechnicalValue value={evidence.response_digest} />
            </dd>
          </div>
        </dl>
      </section>

      <section
        id="live-evidence-governance"
        data-testid="live-evidence-governance"
        className="p-5 sm:p-6"
        aria-labelledby="live-governance-heading"
      >
        <h4
          id="live-governance-heading"
          className="text-lg font-semibold text-slate-950"
        >
          {evidenceT("governanceTitle")}
        </h4>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          {evidenceT("governanceDescription")}
        </p>
        <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(
            [
              [
                evidenceT("aiPlan"),
                evidence.governance.ai_plan_status,
                "positive",
              ],
              [
                evidenceT("approval"),
                evidence.governance.approval_status,
                "neutral",
              ],
              [
                evidenceT("executionGrant"),
                evidence.governance.execution_grant_status,
                "neutral",
              ],
              [
                evidenceT("runnerAuthority"),
                evidence.governance.runner_authority,
                "neutral",
              ],
              [
                evidenceT("review"),
                evidence.governance.review_status,
                "neutral",
              ],
              [
                evidenceT("delivery"),
                evidence.governance.delivery_status,
                "neutral",
              ],
            ] as const
          ).map(([label, value, tone]) => (
            <div key={label} className="rounded-xl border border-slate-200 p-4">
              <dt className="text-xs font-semibold text-slate-500">{label}</dt>
              <dd className="mt-2">
                <StatusPill tone={tone}>
                  {governanceStatus[value] ?? value}
                </StatusPill>
              </dd>
            </div>
          ))}
        </dl>
      </section>
    </article>
  );
}

function LiveEvidence({
  items,
  detail,
  loadingDetail,
  onOpen,
}: {
  items: LiveProviderEvidenceSummary[];
  detail: LiveProviderEvidenceDetail | null;
  loadingDetail: boolean;
  onOpen: (correlation: string) => void;
}) {
  const evidenceT = useTranslations("liveEvidence");
  return (
    <section className="mt-10" aria-labelledby="live-evidence-heading">
      <div>
        <h2
          id="live-evidence-heading"
          className="text-xl font-semibold text-slate-950"
        >
          {evidenceT("title")}
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          {evidenceT("description")}
        </p>
      </div>
      {items.length === 0 ? (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
          <p className="font-semibold text-slate-800">
            {evidenceT("emptyTitle")}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {evidenceT("emptyDescription")}
          </p>
        </div>
      ) : (
        <div className="mt-5 grid gap-3">
          {items.map((item) => (
            <div
              key={item.correlation}
              className="flex min-w-0 flex-col gap-4 rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-slate-950">Zhipu GLM</p>
                  <StatusPill tone="positive">LIVE</StatusPill>
                  <StatusPill tone="positive">
                    {evidenceT("success")}
                  </StatusPill>
                </div>
                <p className="mt-2 text-sm text-slate-700">
                  {item.effective_model_id ?? item.requested_model_id} ·{" "}
                  {evidenceT("summaryUsage", {
                    input: item.input_tokens ?? evidenceT("unknown"),
                    output: item.output_tokens ?? evidenceT("unknown"),
                    total: item.total_tokens ?? evidenceT("unknown"),
                  })}
                </p>
                <div className="mt-2">
                  <TechnicalValue value={item.correlation} visible={12} />
                </div>
              </div>
              <button
                type="button"
                className="min-h-11 shrink-0 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-blue-700 ring-1 ring-blue-200 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                onClick={() => onOpen(item.correlation)}
              >
                {evidenceT("viewDetails")}
              </button>
            </div>
          ))}
        </div>
      )}
      {loadingDetail ? (
        <div
          className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-600"
          role="status"
        >
          {evidenceT("loadingDetail")}
        </div>
      ) : detail ? (
        <EvidenceDetail evidence={detail} />
      ) : null}
    </section>
  );
}

export function ProviderSelector({
  providers,
  value,
  onChange,
  disabled = false,
}: {
  providers: AIProvider[];
  value: CreateAIPlanRequestInput["provider_id"];
  onChange: (providerId: CreateAIPlanRequestInput["provider_id"]) => void;
  disabled?: boolean;
}) {
  const t = useTranslations("providerFoundation");
  const labels = useProviderLabels();
  return (
    <fieldset className="mt-5 min-w-0">
      <legend className="text-sm font-semibold text-slate-950">
        {t("selectorTitle")}
      </legend>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-2">
        <p className="max-w-3xl text-sm leading-6 text-slate-600">
          {t("selectorDescription")}
        </p>
        <Link
          className="rounded-md text-sm font-semibold text-indigo-800 outline-none hover:text-indigo-950 focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
          href="/providers"
        >
          {t("viewStatus")}
        </Link>
      </div>
      <p className="mt-3 rounded-xl bg-indigo-950 px-4 py-3 text-sm font-semibold text-indigo-50">
        {t("evidenceLabel")}
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {providers.map((provider) => {
          const controlDisabled = disabled || !provider.enabled;
          const reasonId = `provider-choice-${provider.provider_id}-reason`;
          return (
            <label
              key={provider.provider_id}
              className={`flex min-w-0 items-start gap-3 rounded-xl border p-4 transition-colors ${provider.provider_id === value ? "border-indigo-500 bg-indigo-50" : "border-slate-200 bg-white"} ${controlDisabled ? "cursor-not-allowed" : "cursor-pointer hover:border-indigo-300"}`}
            >
              <input
                type="radio"
                name="ai-provider"
                value={provider.provider_id}
                checked={provider.provider_id === value}
                disabled={controlDisabled}
                aria-describedby={reasonId}
                aria-label={t("selectAria", {
                  name: labels.providerName[provider.provider_id],
                })}
                onChange={() => onChange(provider.provider_id)}
                className="mt-1 h-4 w-4 shrink-0 accent-indigo-700 outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
              />
              <span className="min-w-0 flex-1">
                <span className="font-semibold break-words text-slate-950">
                  {labels.providerName[provider.provider_id]}
                </span>
                <span
                  id={reasonId}
                  className={`mt-1.5 block text-xs leading-5 ${provider.enabled ? "text-emerald-800" : "text-amber-900"}`}
                >
                  {labels.reason[provider.status_reason]}
                </span>
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function ProviderStatusConsole() {
  const t = useTranslations("providerFoundation");
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [evidence, setEvidence] = useState<LiveProviderEvidenceSummary[]>([]);
  const [detail, setDetail] = useState<LiveProviderEvidenceDetail | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [errorCode, setErrorCode] = useState("");
  const [dialogProvider, setDialogProvider] = useState<AIProvider | null>(null);
  const [disconnecting, setDisconnecting] = useState("");
  const [loadingDetail, setLoadingDetail] = useState(false);

  const load = useCallback(async () => {
    setState("loading");
    setErrorCode("");
    try {
      const [nextProviders, nextEvidence] = await Promise.all([
        listAIProviders(),
        listLiveProviderEvidence(),
      ]);
      setProviders(nextProviders);
      setEvidence(nextEvidence);
      setState("ready");
      if (nextEvidence[0]) {
        setLoadingDetail(true);
        try {
          setDetail(await getLiveProviderEvidence(nextEvidence[0].correlation));
        } finally {
          setLoadingDetail(false);
        }
      }
    } catch (error) {
      setErrorCode(technicalErrorCode(error));
      setState("error");
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function disconnect(provider: AIProvider) {
    setDisconnecting(provider.provider_id);
    setErrorCode("");
    try {
      await disconnectAIProviderCredential(provider.provider_id);
      await load();
    } catch (error) {
      setErrorCode(technicalErrorCode(error));
      setState("error");
    } finally {
      setDisconnecting("");
    }
  }

  async function openEvidence(correlation: string) {
    setLoadingDetail(true);
    try {
      setDetail(await getLiveProviderEvidence(correlation));
    } catch (error) {
      setErrorCode(technicalErrorCode(error));
      setState("error");
    } finally {
      setLoadingDetail(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="border-b border-slate-200 pb-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h1 className="text-3xl font-semibold tracking-tight break-words text-slate-950 sm:text-4xl">
              {t("title")}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
              {t("description")}
            </p>
          </div>
          <StatusPill tone="positive">{t("fixtureDefault")}</StatusPill>
        </div>
        <div className="mt-5 grid gap-3 text-sm md:grid-cols-2">
          <p className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 leading-6 text-indigo-950">
            {t("secretBoundary")}
          </p>
          <p className="rounded-xl border border-slate-200 bg-white p-4 leading-6 text-slate-700">
            {t("authorityBoundary")}
          </p>
        </div>
        <p className="mt-3 rounded-xl bg-indigo-950 px-4 py-3 text-sm font-semibold text-indigo-50">
          {t("evidenceLabel")}
        </p>
      </header>

      {state === "loading" ? (
        <div
          className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600"
          role="status"
        >
          {t("loading")}
        </div>
      ) : null}
      {state === "error" ? (
        <div className="mt-8">
          <ErrorNotice
            title={t("loadFailed")}
            action={t("loadFailedAction")}
            code={errorCode}
          />
          <button
            type="button"
            onClick={() => void load()}
            className="mt-4 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
          >
            {t("retry")}
          </button>
        </div>
      ) : null}
      {state === "ready" ? (
        <>
          <div className="mt-8">
            <ProviderRegistryList
              providers={providers}
              onConfigure={setDialogProvider}
              onDisconnect={(provider) => void disconnect(provider)}
              disconnecting={disconnecting}
            />
          </div>
          <LiveEvidence
            items={evidence}
            detail={detail}
            loadingDetail={loadingDetail}
            onOpen={(correlation) => void openEvidence(correlation)}
          />
        </>
      ) : null}
      <CredentialDialog
        providers={providers}
        initialProvider={dialogProvider}
        onClose={() => setDialogProvider(null)}
        onConnected={load}
      />
    </main>
  );
}
