"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import {
  listAIProviders,
  type AIProvider,
  type CreateAIPlanRequestInput,
} from "@/lib/api";
import { localizeApiError } from "@/lib/localization";

import { StatusPill } from "./status-pill";

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
      missing_local_api_key: t("reason.missing_local_api_key"),
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

function ProviderIdentity({ provider }: { provider: AIProvider }) {
  const t = useTranslations("providerFoundation");
  const labels = useProviderLabels();
  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="min-w-0 text-base font-semibold break-words text-slate-950">
          {labels.providerName[provider.provider_id]}
        </h3>
        <StatusPill tone={provider.enabled ? "positive" : "pending"}>
          {provider.enabled ? t("available") : t("notConfigured")}
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
        <dt className="font-semibold text-slate-500">{t("configuration")}</dt>
        <dd className="mt-1 text-slate-900">
          {provider.configured ? t("configured") : t("notConfigured")}
        </dd>
      </div>
      <div>
        <dt className="font-semibold text-slate-500">{t("runtime")}</dt>
        <dd className="mt-1 text-slate-900">
          {provider.enabled ? t("enabled") : t("disabled")}
        </dd>
      </div>
      <div>
        <dt className="font-semibold text-slate-500">{t("liveValidation")}</dt>
        <dd className="mt-1 text-slate-900">
          {provider.live_validation_status === "fixture_validated"
            ? t("fixtureValidated")
            : t("liveNotPerformed")}
        </dd>
      </div>
    </dl>
  );
}

export function ProviderRegistryList({
  providers,
}: {
  providers: AIProvider[];
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
                className={`mt-3 text-sm leading-6 ${
                  provider.enabled ? "text-emerald-800" : "text-amber-900"
                }`}
              >
                {labels.reason[provider.status_reason]}
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {provider.provider_id === "deterministic-fixture"
                  ? t("fixtureDescription")
                  : t("adapterDescription")}
              </p>
              <a
                className="mt-3 inline-flex rounded-md text-sm font-semibold text-blue-700 outline-none hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
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
          const displayName = labels.providerName[provider.provider_id];
          return (
            <label
              key={provider.provider_id}
              className={`flex min-w-0 items-start gap-3 rounded-xl border transition-colors ${
                provider.provider_id === value
                  ? "border-indigo-500 bg-indigo-50"
                  : "border-slate-200 bg-white"
              } ${provider.enabled ? "p-4 sm:col-span-2 xl:col-span-1" : "p-3 sm:p-4"} ${controlDisabled ? "cursor-not-allowed" : "cursor-pointer hover:border-indigo-300"}`}
            >
              <input
                type="radio"
                name="ai-provider"
                value={provider.provider_id}
                checked={provider.provider_id === value}
                disabled={controlDisabled}
                aria-describedby={reasonId}
                aria-label={t("selectAria", { name: displayName })}
                onChange={() => onChange(provider.provider_id)}
                className="mt-1 h-4 w-4 shrink-0 accent-indigo-700 outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
              />
              <span className="min-w-0 flex-1">
                <span className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1">
                  <span className="font-semibold break-words text-slate-950">
                    {displayName}
                  </span>
                  <code className="font-mono text-xs break-all text-slate-600">
                    {provider.provider_id}
                  </code>
                </span>
                <span
                  id={reasonId}
                  className={`mt-1.5 block text-xs leading-5 ${
                    provider.enabled ? "text-emerald-800" : "text-amber-900"
                  }`}
                >
                  {labels.reason[provider.status_reason]}
                </span>
                {provider.live_validation_status === "not_performed" ? (
                  <span className="mt-1 block text-xs leading-5 text-slate-600">
                    {t("liveNotPerformed")}
                  </span>
                ) : null}
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
  const commonT = useTranslations("common");
  const errorT = useTranslations("errors");
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setState("loading");
    setMessage("");
    try {
      setProviders(await listAIProviders());
      setState("ready");
    } catch (error) {
      setMessage(localizeApiError(error, errorT));
      setState("error");
    }
  }, [errorT]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="border-b border-slate-200 pb-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
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
        <div
          className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6"
          role="alert"
        >
          <p className="font-semibold text-red-950">{t("loadFailed")}</p>
          <p className="mt-2 text-sm text-red-800">{message}</p>
          <button
            type="button"
            onClick={() => void load()}
            className="mt-4 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-red-800 ring-1 ring-red-300 outline-none hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
          >
            {commonT("actions.retry")}
          </button>
        </div>
      ) : null}

      {state === "ready" ? (
        <div className="mt-8">
          <ProviderRegistryList providers={providers} />
        </div>
      ) : null}
    </main>
  );
}
