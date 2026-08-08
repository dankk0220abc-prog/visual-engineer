import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const webPort = Number(process.env.WEB_PORT ?? "3000");
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${webPort}`;
const providerEvidenceReporter = path.join(
  __dirname,
  "e2e/support/provider-evidence-safe-reporter.ts",
);
const providerFoundationSpec = /provider-foundation\.spec\.ts$/;
const providerEvidenceHarnessSpec =
  /provider-evidence-safety-harness\.spec\.ts$/;
const providerEvidenceNegativeSpec =
  /provider-evidence-safety-negative\.spec\.ts$/;
const providerEvidenceSpecs = [
  providerFoundationSpec,
  providerEvidenceHarnessSpec,
  providerEvidenceNegativeSpec,
];

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI
    ? [[providerEvidenceReporter], ["line"], ["html", { open: "never" }]]
    : [[providerEvidenceReporter], ["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "desktop-chromium",
      testIgnore: providerEvidenceSpecs,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1000 },
      },
    },
    {
      name: "narrow-chromium",
      testIgnore: providerEvidenceSpecs,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 390, height: 844 },
      },
    },
    {
      name: "provider-evidence-desktop-chromium",
      testMatch: [providerFoundationSpec, providerEvidenceHarnessSpec],
      retries: 0,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1000 },
        trace: "off",
        screenshot: "off",
        video: "off",
      },
    },
    {
      name: "provider-evidence-narrow-chromium",
      testMatch: providerFoundationSpec,
      retries: 0,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 390, height: 844 },
        trace: "off",
        screenshot: "off",
        video: "off",
      },
    },
  ],
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: `pnpm dev --hostname 127.0.0.1 --port ${webPort}`,
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
        env: {
          NEXT_PUBLIC_API_BASE_URL:
            process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000",
        },
      },
});
