import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Windows 未开启开发者模式时无法创建 pnpm 依赖符号链接；容器仍输出精简 standalone。
  ...(process.platform === "win32" ? {} : { output: "standalone" as const }),
  poweredByHeader: false,
  productionBrowserSourceMaps: false,
  transpilePackages: ["@case-filing/contracts", "@case-filing/design-tokens", "@case-filing/ui"]
};

export default nextConfig;
