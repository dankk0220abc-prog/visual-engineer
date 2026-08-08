import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const outputDirectory = process.env.PLAYWRIGHT_PROVIDER_EVIDENCE_OUTPUT_DIR;

if (outputDirectory === undefined || outputDirectory.length === 0) {
  throw new Error("VE_PROVIDER_EVIDENCE_OUTPUT_DIR_REQUIRED");
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /provider-evidence-safety-negative\.spec\.ts$/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  preserveOutput: "never",
  outputDir: outputDirectory,
  reporter: [
    [path.join(__dirname, "e2e/support/provider-evidence-safe-reporter.ts")],
    ["json"],
  ],
  use: {
    ...devices["Desktop Chrome"],
    trace: "off",
    screenshot: "off",
    video: "off",
  },
  projects: [
    {
      name: "provider-evidence-negative-chromium",
      retries: 0,
      use: {
        trace: "off",
        screenshot: "off",
        video: "off",
      },
    },
  ],
});
