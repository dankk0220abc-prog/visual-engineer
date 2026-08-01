"use client";

import { useTranslations } from "next-intl";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations();
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl items-center px-4">
      <div className="w-full rounded-2xl border border-red-200 bg-red-50 p-8 text-center">
        <h1 className="text-xl font-semibold text-red-950">
          {t("appStates.errorTitle")}
        </h1>
        <p className="mt-2 text-sm text-red-800">
          {t("appStates.errorDescription")}
        </p>
        <button
          className="mt-5 rounded-xl bg-red-900 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-red-800 focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
          type="button"
          onClick={reset}
        >
          {t("common.actions.retry")}
        </button>
      </div>
    </main>
  );
}
