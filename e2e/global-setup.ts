import { execFileSync } from "node:child_process";
import path from "node:path";

export default function globalSetup() {
  const root = path.resolve(import.meta.dirname, "..");
  const python = path.join(root, "services", "api", ".venv", "Scripts", "python.exe");
  const script = path.join(root, "scripts", "create-e2e-fixtures.py");
  const output = path.join(root, ".artifacts", "e2e-fixtures");
  execFileSync(python, [script, output], { stdio: "inherit" });
}
