import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "VisualEngineer · Phase 2",
  description:
    "面向企业前端团队的 VisualEngineer 受治理只读仓库调查与计划审批控制台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
