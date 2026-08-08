import type { Reporter, TestCase, TestResult } from "@playwright/test/reporter";

const providerEvidenceFailurePrefix = "VE_PROVIDER_EVIDENCE_";

export default class ProviderEvidenceSafeReporter implements Reporter {
  private failureCode: string | null = null;

  onTestEnd(_test: TestCase, result: TestResult): void {
    const failure = result.annotations.find((annotation) =>
      annotation.type.startsWith(providerEvidenceFailurePrefix),
    );
    if (failure !== undefined && this.failureCode === null) {
      this.failureCode = failure.type;
    }
  }

  async onEnd(): Promise<{ status: "failed" } | undefined> {
    if (this.failureCode === null) return undefined;
    process.stderr.write(`${this.failureCode}\n`);
    return { status: "failed" };
  }

  printsToStdio(): boolean {
    return false;
  }
}
