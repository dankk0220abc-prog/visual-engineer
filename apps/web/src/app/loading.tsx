import { getTranslations } from "next-intl/server";

export default async function Loading() {
  const t = await getTranslations("appStates");
  return (
    <main className="mx-auto flex min-h-screen max-w-7xl items-center justify-center px-4">
      <p className="text-sm text-slate-600" role="status">
        {t("loading")}
      </p>
    </main>
  );
}
