"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "任务" },
  { href: "/runners", label: "Runners" },
  { href: "/repositories", label: "Repositories" },
  { href: "/execution-grants", label: "Grants" },
  { href: "/workspaces", label: "Workspaces" },
];

export function MainNavigation() {
  const pathname = usePathname();

  return (
    <nav
      className="border-b border-slate-200 bg-white/90 backdrop-blur"
      aria-label="主导航"
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
        </div>
      </div>
    </nav>
  );
}
