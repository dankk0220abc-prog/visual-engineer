import { describe, expect, it } from "vitest";

import playwrightConfig from "../../playwright.config";
import {
  enforceProviderEvidenceSafety,
  PROVIDER_EVIDENCE_SECRET_LEAK,
  scanProviderEvidenceText,
} from "./provider-evidence-safety";

const syntheticSecret = ["ve", "synthetic", "provider", "key", "only"].join(
  "-",
);

describe("provider evidence safety", () => {
  it("isolates Provider Evidence projects from ordinary failure artifacts", () => {
    const projects = playwrightConfig.projects ?? [];
    const providerProjects = projects.filter((project) =>
      project.name?.startsWith("provider-evidence-"),
    );
    const ordinaryProjects = projects.filter((project) =>
      ["desktop-chromium", "narrow-chromium"].includes(project.name ?? ""),
    );

    expect(playwrightConfig.use).toMatchObject({
      trace: "retain-on-failure",
      screenshot: "only-on-failure",
      video: "retain-on-failure",
    });
    expect(providerProjects).toHaveLength(2);
    for (const project of providerProjects) {
      expect(project.retries).toBe(0);
      expect(project.use).toMatchObject({
        trace: "off",
        screenshot: "off",
        video: "off",
      });
    }
    expect(ordinaryProjects).toHaveLength(2);
    for (const project of ordinaryProjects) {
      const ignored = Array.isArray(project.testIgnore)
        ? project.testIgnore.map(String)
        : [String(project.testIgnore)];
      expect(ignored).toEqual(
        expect.arrayContaining([
          expect.stringMatching(/provider-foundation/),
          expect.stringMatching(/provider-evidence-safety-harness/),
          expect.stringMatching(/provider-evidence-safety-negative/),
        ]),
      );
    }
  });

  it("passes safe DOM text without retaining the checked value", () => {
    const record = enforceProviderEvidenceSafety("Fixture provider status", {
      forbiddenPatterns: [/Authorization/i],
      secretValues: [syntheticSecret],
    });

    expect(record).toEqual({
      rule_id: PROVIDER_EVIDENCE_SECRET_LEAK,
      checked_value_count: 1,
      result: "passed",
      error_category: null,
    });
    expect(JSON.stringify(record).includes(syntheticSecret)).toBe(false);
  });

  it("returns only a fixed failure record when one of several values leaks", () => {
    const otherSecret = ["another", "synthetic", "value"].join("-");
    const record = scanProviderEvidenceText(
      `Provider status accidentally contained ${syntheticSecret}`,
      {
        forbiddenPatterns: [],
        secretValues: [otherSecret, syntheticSecret],
      },
    );
    const serialized = JSON.stringify(record);

    expect(record).toEqual({
      rule_id: PROVIDER_EVIDENCE_SECRET_LEAK,
      checked_value_count: 2,
      result: "failed",
      error_category: PROVIDER_EVIDENCE_SECRET_LEAK,
    });
    expect(serialized.includes(syntheticSecret)).toBe(false);
    expect(serialized.includes(otherSecret)).toBe(false);
    expect(Object.keys(record).sort()).toEqual([
      "checked_value_count",
      "error_category",
      "result",
      "rule_id",
    ]);
  });

  it("throws a fixed error without the secret or received DOM in message or stack", () => {
    const visibleText = `Large received DOM ${syntheticSecret} private marker`;
    let caught: Error | null = null;
    try {
      enforceProviderEvidenceSafety(visibleText, {
        forbiddenPatterns: [],
        secretValues: [syntheticSecret],
      });
    } catch (error) {
      caught = error instanceof Error ? error : null;
    }

    expect(caught?.message).toBe(PROVIDER_EVIDENCE_SECRET_LEAK);
    const capturedFailure = `${caught?.message ?? ""}\n${caught?.stack ?? ""}`;
    expect(capturedFailure.includes(syntheticSecret)).toBe(false);
    expect(capturedFailure.includes(visibleText)).toBe(false);
    expect(capturedFailure.includes("private marker")).toBe(false);
  });

  it("uses the same fixed error for a forbidden-pattern DOM leak", () => {
    const visibleText = "Authorization: sensitive browser output";
    let message = "";
    try {
      enforceProviderEvidenceSafety(visibleText, {
        forbiddenPatterns: [/\bAuthorization\b/i],
        secretValues: [],
      });
    } catch (error) {
      message = error instanceof Error ? error.message : "";
    }

    expect(message).toBe(PROVIDER_EVIDENCE_SECRET_LEAK);
    expect(message.includes(visibleText)).toBe(false);
  });

  it("does not treat empty values as probes", () => {
    const record = scanProviderEvidenceText("Visible fixture text", {
      forbiddenPatterns: [],
      secretValues: ["", syntheticSecret],
    });

    expect(record.result).toBe("passed");
    expect(record.checked_value_count).toBe(1);
  });
});
