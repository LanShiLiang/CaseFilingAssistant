import type { Metadata } from "next";
import type { CSSProperties, ReactNode } from "react";

import { tokens } from "@case-filing/design-tokens";

import { AppProviders } from "@/store/AppProviders";

import "./globals.css";

export const metadata: Metadata = {
  title: "Case Filing Assistant",
  description: "本地申请强制执行材料草稿助手"
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const tokenStyles = {
    "--canvas": tokens.color.canvas,
    "--surface": tokens.color.surface,
    "--surface-soft": tokens.color.surfaceSoft,
    "--ink": tokens.color.ink,
    "--muted": tokens.color.muted,
    "--line": tokens.color.line,
    "--brand": tokens.color.brand,
    "--brand-hover": tokens.color.brandHover,
    "--accent": tokens.color.accent,
    "--success": tokens.color.success,
    "--warning": tokens.color.warning,
    "--danger": tokens.color.danger
  } as CSSProperties;
  return (
    <html lang="zh-CN">
      <body style={tokenStyles}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
