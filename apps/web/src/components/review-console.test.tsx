import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createReviewPackage,
  decideReviewPackage,
  evaluateReleaseReadiness,
  listReviewPackages,
  listValidationSuiteRuns,
  refreshReviewPackage,
  type ReviewPackage,
  type ValidationSuiteRun,
} from "@/lib/api";

import { ReviewConsole } from "./review-console";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    createReviewPackage: vi.fn(),
    decideReviewPackage: vi.fn(),
    evaluateReleaseReadiness: vi.fn(),
    listReviewPackages: vi.fn(),
    listValidationSuiteRuns: vi.fn(),
    refreshReviewPackage: vi.fn(),
  };
});

const successfulSuite = {
  id: "10000000-0000-4000-8000-000000000001",
  suite_id: "fixture-integrity-suite-v1",
  suite_version: 1,
  state: "succeeded",
  checkpoint_id: "20000000-0000-4000-8000-000000000001",
  result: { verdict: "succeeded" },
} as ValidationSuiteRun;

const reviewPackage = {
  id: "30000000-0000-4000-8000-000000000001",
  schema_version: 2,
  package_version: 1,
  freshness_state_id: "31000000-0000-4000-8000-000000000001",
  freshness_generation: 1,
  current_freshness_generation: 1,
  run_id: "40000000-0000-4000-8000-000000000001",
  plan_id: "50000000-0000-4000-8000-000000000001",
  repository_handle_id: "60000000-0000-4000-8000-000000000001",
  source_revision: "a".repeat(40),
  workspace_id: "70000000-0000-4000-8000-000000000001",
  checkpoint_id: successfulSuite.checkpoint_id,
  checkpoint_fingerprint: "b".repeat(64),
  checkpoint_diff_hash: "f".repeat(64),
  suite_run_id: successfulSuite.id,
  suite_result_id: "80000000-0000-4000-8000-000000000001",
  execution_grant_id: "81000000-0000-4000-8000-000000000001",
  suite_policy_digest: "9".repeat(64),
  suite_result_digest: "c".repeat(64),
  evidence_manifest: {
    schema_version: 2,
    entries: [
      {
        sequence: 1,
        step_id: "fixture-contract",
        evidence_id: "90000000-0000-4000-8000-000000000001",
      },
      {
        sequence: 2,
        step_id: "fixture-manifest",
        evidence_id: "90000000-0000-4000-8000-000000000002",
      },
    ],
  },
  evidence_manifest_digest: "d".repeat(64),
  blocker_summary: {
    schema_version: 1,
    source: "governed-review-security-findings",
    source_version: 1,
    critical_count: 0,
    high_count: 0,
    blocking_medium_count: 0,
    findings: [],
  },
  blocker_summary_digest: "8".repeat(64),
  blocker_source: "governed-review-security-findings",
  blocker_source_version: 1,
  critical_count: 0,
  high_count: 0,
  blocking_medium_count: 0,
  package_digest: "e".repeat(64),
  freshness: "fresh",
  stale_reason_code: null,
  git_authorization: false,
  deployment_authorization: false,
  created_at: "2026-07-30T08:00:00Z",
  invalidation: null,
  decision: null,
  readiness: null,
} satisfies ReviewPackage;

describe("ReviewConsole", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listValidationSuiteRuns).mockResolvedValue([]);
    vi.mocked(listReviewPackages).mockResolvedValue([]);
  });

  it("creates a package only from a successful Suite candidate", async () => {
    vi.mocked(listValidationSuiteRuns).mockResolvedValue([successfulSuite]);
    vi.mocked(createReviewPackage).mockResolvedValue(reviewPackage);
    render(<ReviewConsole />);

    const button = await screen.findByRole("button", {
      name: "Create immutable Review Package",
    });
    fireEvent.click(button);
    await waitFor(() =>
      expect(createReviewPackage).toHaveBeenCalledWith(
        { suite_run_id: successfulSuite.id },
        expect.stringContaining(`review-package-${successfulSuite.id}-`),
      ),
    );
  });

  it("shows manifest authority separation and drives decision/readiness controls", async () => {
    vi.mocked(listReviewPackages).mockResolvedValue([reviewPackage]);
    vi.mocked(refreshReviewPackage).mockResolvedValue(reviewPackage);
    vi.mocked(decideReviewPackage).mockResolvedValue({
      ...reviewPackage,
      decision: {
        id: "a0000000-0000-4000-8000-000000000001",
        review_package_id: reviewPackage.id,
        package_version: reviewPackage.package_version,
        expected_generation: reviewPackage.freshness_generation,
        package_digest: reviewPackage.package_digest,
        policy_digest: reviewPackage.suite_policy_digest,
        decision: "approve",
        reason: "Reviewed exact immutable Evidence Manifest.",
        actor_type: "local_user",
        idempotency_key: "review-decision-test",
        idempotency_request_hash: "6".repeat(64),
        decision_digest: "7".repeat(64),
        request_id: "review-test",
        git_authorization: false,
        deployment_authorization: false,
        created_at: "2026-07-30T08:01:00Z",
      },
    });
    vi.mocked(evaluateReleaseReadiness).mockResolvedValue(reviewPackage);
    render(<ReviewConsole />);

    expect(await screen.findByText("Evidence Manifest 2/2")).toBeVisible();
    expect(screen.getByText("Generation 1 / current 1")).toBeVisible();
    expect(
      screen.getByText("Critical 0 · High 0 · Blocking medium 0"),
    ).toBeVisible();
    expect(
      screen.getByText(
        "Git authorization: false · Deployment authorization: false",
      ),
    ).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Recheck freshness" }));
    await waitFor(() =>
      expect(refreshReviewPackage).toHaveBeenCalledWith(reviewPackage.id),
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Approve Review Package" }),
    );
    await waitFor(() =>
      expect(decideReviewPackage).toHaveBeenCalledWith(
        reviewPackage.id,
        {
          decision: "approve",
          reason: "Reviewed exact immutable Evidence Manifest.",
          expected_generation: reviewPackage.freshness_generation,
        },
        `review-decision-${reviewPackage.id}-g${reviewPackage.freshness_generation}-approve`,
      ),
    );
  });
});
