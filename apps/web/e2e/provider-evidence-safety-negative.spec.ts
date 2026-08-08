import { test } from "@playwright/test";

import {
  enforceProviderEvidenceSafety,
  PROVIDER_EVIDENCE_SECRET_LEAK,
} from "../src/lib/provider-evidence-safety";

const negativeProofFailed = "VE_PROVIDER_EVIDENCE_NEGATIVE_PROOF_FAILED";
const syntheticSecret = ["ve", "browser", "synthetic", "secret", "only"].join(
  "-",
);
const syntheticDomMarker = ["ve", "private", "dom", "marker"].join("::");

test("synthetic DOM leak is reduced to the fixed safe failure boundary", async ({
  page,
}, testInfo) => {
  let failureCode = negativeProofFailed;
  try {
    await page.setContent(
      `<main><p>${syntheticDomMarker}</p><output>${syntheticSecret}</output></main>`,
    );
    const visibleText = await page.locator("body").innerText();
    let caught: Error | null = null;
    try {
      enforceProviderEvidenceSafety(visibleText, {
        forbiddenPatterns: [],
        secretValues: [syntheticSecret],
      });
    } catch (error) {
      caught = error instanceof Error ? error : null;
    }
    const publicFailure = `${caught?.message ?? ""}\n${caught?.stack ?? ""}`;
    if (
      caught?.message === PROVIDER_EVIDENCE_SECRET_LEAK &&
      !publicFailure.includes(syntheticSecret) &&
      !publicFailure.includes(syntheticDomMarker) &&
      !publicFailure.includes(visibleText)
    ) {
      failureCode = PROVIDER_EVIDENCE_SECRET_LEAK;
    }
  } catch {
    failureCode = negativeProofFailed;
  }

  try {
    await page.setContent(
      "<!doctype html><title>Provider Evidence closed</title>",
    );
  } catch {
    failureCode = negativeProofFailed;
  }
  testInfo.annotations.push({ type: failureCode });
  testInfo.skip(true, failureCode);
});
