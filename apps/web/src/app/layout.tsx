import type { Metadata } from "next";

import { MainNavigation } from "@/components/main-navigation";

import "./globals.css";

export const metadata: Metadata = {
  title: "VisualEngineer · Phase 3",
  description: "VisualEngineer 受治理控制面与浏览器编排的仓库无关 Local Runner",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <MainNavigation />
        {children}
      </body>
    </html>
  );
}
