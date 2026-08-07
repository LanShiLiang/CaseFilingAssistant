import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": new URL("./src", import.meta.url).pathname }
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/test/**"],
      // 当前基线覆盖 App Router 与所有前端业务源文件；阈值按真实全量覆盖率设置，后续只允许提高。
      thresholds: { lines: 23, functions: 23, branches: 23, statements: 23 }
    }
  }
});
