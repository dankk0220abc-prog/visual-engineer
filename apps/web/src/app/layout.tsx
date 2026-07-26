import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "VisualEngineer · Foundation",
  description:
    "面向企业前端团队的 VisualEngineer 受治理交付 Foundation 任务控制台",
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
