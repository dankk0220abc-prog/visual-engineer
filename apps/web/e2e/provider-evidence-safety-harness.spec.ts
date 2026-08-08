import { spawn } from "node:child_process";
import { mkdtemp, readdir, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { test } from "@playwright/test";

import { PROVIDER_EVIDENCE_SECRET_LEAK } from "../src/lib/provider-evidence-safety";

const harnessFailure = "VE_PROVIDER_EVIDENCE_HARNESS_FAILED";
const syntheticSecret = ["ve", "browser", "synthetic", "secret", "only"].join(
  "-",
);
const syntheticDomMarker = ["ve", "private", "dom", "marker"].join("::");
const webRoot = path.resolve(__dirname, "..");
const playwrightCli = path.join(
  webRoot,
  "node_modules/@playwright/test/cli.js",
);

type ChildResult = {
  code: number | null;
  signal: NodeJS.Signals | null;
  stdout: string;
  stderr: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function collectResultRecords(
  value: unknown,
  records: Record<string, unknown>[],
): void {
  if (Array.isArray(value)) {
    for (const item of value) collectResultRecords(item, records);
    return;
  }
  if (!isRecord(value)) return;
  if (Array.isArray(value.results) && typeof value.projectName === "string") {
    records.push(value);
  }
  for (const nested of Object.values(value))
    collectResultRecords(nested, records);
}

async function runNegativeProof(outputDirectory: string): Promise<ChildResult> {
  return await new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [
        playwrightCli,
        "test",
        "--config=playwright.provider-evidence-negative.config.ts",
        "--last-failed-file",
        "/dev/null",
      ],
      {
        cwd: webRoot,
        env: {
          PATH: process.env.PATH,
          HOME: process.env.HOME,
          NODE_ENV: process.env.NODE_ENV ?? "test",
          PLAYWRIGHT_BROWSERS_PATH: process.env.PLAYWRIGHT_BROWSERS_PATH,
          PLAYWRIGHT_PROVIDER_EVIDENCE_OUTPUT_DIR: outputDirectory,
          CI: "1",
        },
        stdio: "pipe",
      },
    );
    child.stdin.end();
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk: string) => {
      stderr += chunk;
    });
    child.once("error", reject);
    child.once("close", (code, signal) => {
      resolve({ code, signal, stdout, stderr });
    });
  });
}

function negativeProofIsSafe(
  child: ChildResult,
  report: unknown,
  outputEntries: string[],
): boolean {
  const combinedOutput = `${child.stdout}\n${child.stderr}`;
  if (
    child.code !== 1 ||
    child.signal !== null ||
    !child.stderr.includes(PROVIDER_EVIDENCE_SECRET_LEAK) ||
    combinedOutput.includes(syntheticSecret) ||
    combinedOutput.includes(syntheticDomMarker) ||
    outputEntries.length !== 0 ||
    !isRecord(report) ||
    !isRecord(report.config) ||
    !Array.isArray(report.config.projects)
  ) {
    return false;
  }
  const projects = report.config.projects.filter(isRecord);
  if (
    projects.length !== 1 ||
    projects[0]?.name !== "provider-evidence-negative-chromium" ||
    projects[0]?.retries !== 0
  ) {
    return false;
  }
  const resultRecords: Record<string, unknown>[] = [];
  collectResultRecords(report.suites, resultRecords);
  if (resultRecords.length !== 1) return false;
  const results = resultRecords[0]?.results;
  if (
    !Array.isArray(results) ||
    results.length !== 1 ||
    !isRecord(results[0])
  ) {
    return false;
  }
  const result = results[0];
  return (
    result.retry === 0 &&
    result.status === "skipped" &&
    Array.isArray(result.attachments) &&
    result.attachments.length === 0 &&
    Array.isArray(result.stdout) &&
    result.stdout.length === 0 &&
    Array.isArray(result.stderr) &&
    result.stderr.length === 0
  );
}

test("real browser synthetic leak produces no sensitive failure artifact", async ({}, testInfo) => {
  const temporaryRoot = await mkdtemp(
    path.join(os.tmpdir(), "visualengineer-provider-evidence-"),
  );
  const outputDirectory = path.join(temporaryRoot, "artifacts");
  let failureCode: string | null = harnessFailure;
  try {
    const child = await runNegativeProof(outputDirectory);
    let report: unknown = null;
    try {
      report = JSON.parse(child.stdout) as unknown;
    } catch {
      report = null;
    }
    let outputEntries: string[] = [];
    try {
      outputEntries = await readdir(outputDirectory, { recursive: true });
    } catch (error) {
      if (!isRecord(error) || error.code !== "ENOENT") throw error;
    }
    if (negativeProofIsSafe(child, report, outputEntries)) {
      failureCode = null;
    }
  } catch {
    failureCode = harnessFailure;
  } finally {
    try {
      await rm(temporaryRoot, { recursive: true, force: true });
    } catch {
      failureCode = harnessFailure;
    }
  }

  if (failureCode !== null) {
    testInfo.annotations.push({ type: failureCode });
    testInfo.skip(true, failureCode);
  }
});
