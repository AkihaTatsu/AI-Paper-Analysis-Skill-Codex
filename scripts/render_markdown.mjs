import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repository = resolve(fileURLToPath(new URL("..", import.meta.url)));
const renderer = join(repository, "scripts", "render_report.mjs");
const reports = [
  join(repository, "templates", "paper-report.md"),
  join(repository, "templates", "category-report.md"),
  join(repository, "tests", "fixtures", "portable-report.md"),
];
const environment = { ...process.env };
if (!environment.APA_PYTHON) {
  const candidates = [
    join(repository, ".venv", "bin", "python"),
    join(repository, ".venv", "Scripts", "python.exe"),
  ];
  const python = candidates.find((candidate) => existsSync(candidate));
  if (python) environment.APA_PYTHON = python;
}

for (const report of reports) {
  execFileSync(process.execPath, [renderer, report], { env: environment, stdio: "inherit" });
}

process.stdout.write("All report rendering fixtures passed.\n");
