"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

import type { Task } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";

import { StatusPill } from "./status-pill";

export function TaskCard({ task }: { task: Task }) {
  const locale = useLocale();
  const t = useTranslations("taskCard");
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-slate-300">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">
            {task.title}
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            {task.repository_display_name}
          </p>
        </div>
        <StatusPill tone="neutral">{task.status}</StatusPill>
      </div>
      <p className="mt-4 line-clamp-2 text-sm leading-6 text-slate-600">
        {task.objective}
      </p>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
        <time className="text-xs text-slate-500" dateTime={task.created_at}>
          {formatTimestamp(task.created_at, locale)}
        </time>
        <Link
          className="rounded-lg px-2 py-1 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
          href={`/tasks/${task.id}`}
        >
          {t("viewDetails")}
          <span aria-hidden="true"> →</span>
        </Link>
      </div>
    </article>
  );
}
