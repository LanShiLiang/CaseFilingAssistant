import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppProviders } from "@/store/AppProviders";

import "./globals.css";

export const metadata: Metadata = {
  title: "Case Filing Assistant",
  description: "本地申请强制执行材料草稿助手"
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
