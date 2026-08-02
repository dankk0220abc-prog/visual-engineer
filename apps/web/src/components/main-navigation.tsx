"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { LocaleSwitcher } from "./locale-switcher";

export function MainNavigation() {
  const pathname = usePathname();
  const t = useTranslations("navigation");
  const links = [
    { href: "/", label: t("tasks") },
    { href: "/runners", label: t("runners") },
    { href: "/repositories", label: t("repositories") },
    { href: "/execution-grants", label: t("executionGrants") },
    { href: "/workspaces", label: t("workspaces") },
    { href: "/validations", label: t("validations") },
    { href: "/reviews", label: t("reviews") },
    { href: "/deliveries", label: t("deliveries") },
  ];

  return (
    <nav
      className="border-b border-slate-200 bg-white/90 backdrop-blur"
      aria-label={t("label")}
    >
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-3 sm:gap-4 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="text-sm font-bold tracking-wide text-slate-950 outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
        >
          VisualEngineer
        </Link>
        <div className="flex flex-wrap items-center justify-end gap-1">
          {links.map((link) => {
            const current =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={current ? "page" : undefined}
                className={`rounded-lg px-3 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 ${
                  current
                    ? "bg-blue-50 text-blue-800"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          <LocaleSwitcher />
        </div>
      </div>
    </nav>
  );
}
