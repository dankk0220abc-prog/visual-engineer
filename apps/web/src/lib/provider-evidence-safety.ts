export const PROVIDER_EVIDENCE_SECRET_LEAK = "VE_PROVIDER_EVIDENCE_SECRET_LEAK";

export type ProviderEvidenceSafetyRecord = {
  rule_id: "VE_PROVIDER_EVIDENCE_SECRET_LEAK";
  checked_value_count: number;
  result: "passed" | "failed";
  error_category: "VE_PROVIDER_EVIDENCE_SECRET_LEAK" | null;
};

type ProviderEvidenceSafetyInput = {
  forbiddenPatterns: readonly RegExp[];
  secretValues: readonly string[];
};

export function scanProviderEvidenceText(
  visibleText: string,
  input: ProviderEvidenceSafetyInput,
): ProviderEvidenceSafetyRecord {
  const checkedValues = input.secretValues.filter((value) => value.length > 0);
  const patternLeak = input.forbiddenPatterns.some((pattern) => {
    pattern.lastIndex = 0;
    return pattern.test(visibleText);
  });
  const valueLeak = checkedValues.some((value) => visibleText.includes(value));
  const failed = patternLeak || valueLeak;
  return {
    rule_id: PROVIDER_EVIDENCE_SECRET_LEAK,
    checked_value_count: checkedValues.length,
    result: failed ? "failed" : "passed",
    error_category: failed ? PROVIDER_EVIDENCE_SECRET_LEAK : null,
  };
}

export function enforceProviderEvidenceSafety(
  visibleText: string,
  input: ProviderEvidenceSafetyInput,
): ProviderEvidenceSafetyRecord {
  const record = scanProviderEvidenceText(visibleText, input);
  if (record.result === "failed") {
    throw new Error(PROVIDER_EVIDENCE_SECRET_LEAK);
  }
  return record;
}
