import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createDeliveryAuthorization,
  decideDeliveryAuthorization,
  dispatchLocalDelivery,
  listDeliveryAuthorizations,
  listReviewPackages,
  type DeliveryAuthorization,
  type ReviewPackage,
} from "@/lib/api";

import { DeliveryConsole } from "./delivery-console";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    createDeliveryAuthorization: vi.fn(),
    decideDeliveryAuthorization: vi.fn(),
    dispatchLocalDelivery: vi.fn(),
    listDeliveryAuthorizations: vi.fn(),
    listReviewPackages: vi.fn(),
  };
});

const reviewPackage = {
  id: "30000000-0000-4000-8000-000000000001",
  freshness: "fresh",
  freshness_generation: 2,
  checkpoint_id: "20000000-0000-4000-8000-000000000001",
  decision: { decision: "approve" },
  readiness: { verdict: "ready", effective_verdict: "ready" },
} as ReviewPackage;

const authorization = {
  id: "40000000-0000-4000-8000-000000000001",
  authorization_version: 1,
  review_package_id: reviewPackage.id,
  review_decision_id: "41000000-0000-4000-8000-000000000001",
  readiness_verdict_id: "42000000-0000-4000-8000-000000000001",
  freshness_generation: 2,
  package_digest: "1".repeat(64),
  decision_digest: "2".repeat(64),
  readiness_digest: "3".repeat(64),
  execution_grant_id: "43000000-0000-4000-8000-000000000001",
  workspace_id: "50000000-0000-4000-8000-000000000001",
  checkpoint_id: reviewPackage.checkpoint_id,
  checkpoint_fingerprint: "4".repeat(64),
  checkpoint_diff_hash: "5".repeat(64),
  repository_handle_id: "60000000-0000-4000-8000-000000000001",
  source_revision: "6".repeat(40),
  branch_ref: "refs/heads/visual-engineer/50000000000040008000000000000001",
  commit_message: "VisualEngineer: governed local delivery 40000000",
  local_git_commit_access: true,
  remote_access: false,
  push_access: false,
  pull_request_access: false,
  tag_access: false,
  deployment_access: false,
  source_repository_write_access: false,
  status: "pending",
  policy_hash: "7".repeat(64),
  created_at: "2026-07-31T08:00:00Z",
  decided_at: null,
  dispatched_at: null,
  terminal_at: null,
  expires_at: "2026-07-31T08:15:00Z",
  error_code: null,
  decision: null,
  job: null,
  delivery: null,
} satisfies DeliveryAuthorization;

describe("DeliveryConsole", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listReviewPackages).mockResolvedValue([]);
    vi.mocked(listDeliveryAuthorizations).mockResolvedValue([]);
  });

  it("offers only a fresh approved ready Review as a delivery candidate", async () => {
    vi.mocked(listReviewPackages).mockResolvedValue([reviewPackage]);
    vi.mocked(createDeliveryAuthorization).mockResolvedValue(authorization);
    render(<DeliveryConsole />);

    const button = await screen.findByRole("button", {
      name: "Create Delivery Authorization",
    });
    expect(
      screen.queryByText(
        "Local commit only · remote/push/PR/tag/deploy denied",
      ),
    ).not.toBeInTheDocument();
    fireEvent.click(button);
    await waitFor(() =>
      expect(createDeliveryAuthorization).toHaveBeenCalledWith(
        { review_package_id: reviewPackage.id },
        expect.stringContaining(`delivery-authorization-${reviewPackage.id}-`),
      ),
    );
  });

  it("requires a separate decision and never exposes remote authority", async () => {
    vi.mocked(listDeliveryAuthorizations).mockResolvedValue([authorization]);
    vi.mocked(decideDeliveryAuthorization).mockResolvedValue({
      ...authorization,
      status: "approved",
    });
    render(<DeliveryConsole />);

    expect(
      await screen.findByText(
        "Local commit only · remote/push/PR/tag/deploy denied",
      ),
    ).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: "Approve local commit" }),
    );
    await waitFor(() =>
      expect(decideDeliveryAuthorization).toHaveBeenCalledWith(
        authorization.id,
        { decision: "approve", reason: null },
        expect.stringContaining(`delivery-approve-${authorization.id}-`),
      ),
    );
    expect(
      screen.queryByRole("button", { name: /push|pull request|deploy/i }),
    ).not.toBeInTheDocument();
  });

  it("dispatches only an already approved authorization", async () => {
    const approved = {
      ...authorization,
      status: "approved" as const,
      decided_at: "2026-07-31T08:01:00Z",
    };
    const dispatched = {
      ...approved,
      status: "dispatched" as const,
      dispatched_at: "2026-07-31T08:02:00Z",
    };
    const succeeded = {
      ...dispatched,
      status: "succeeded" as const,
      terminal_at: "2026-07-31T08:02:01Z",
      delivery: {
        id: "70000000-0000-4000-8000-000000000001",
        delivery_authorization_id: authorization.id,
        runner_job_id: "71000000-0000-4000-8000-000000000001",
        runner_attempt_id: "72000000-0000-4000-8000-000000000001",
        side_effect_permit_id: "73000000-0000-4000-8000-000000000001",
        workspace_id: authorization.workspace_id,
        checkpoint_id: authorization.checkpoint_id,
        checkpoint_fingerprint: authorization.checkpoint_fingerprint,
        checkpoint_diff_hash: authorization.checkpoint_diff_hash,
        branch_ref: authorization.branch_ref,
        commit_oid: "8".repeat(40),
        tree_oid: "9".repeat(40),
        parent_oid: authorization.source_revision,
        result_digest: "a".repeat(64),
        remote_access: false as const,
        pushed: false as const,
        pull_request_created: false as const,
        tagged: false as const,
        deployed: false as const,
        created_at: "2026-07-31T08:02:01Z",
      },
    };
    vi.mocked(listDeliveryAuthorizations)
      .mockResolvedValueOnce([approved])
      .mockResolvedValueOnce([dispatched])
      .mockResolvedValue([succeeded]);
    vi.mocked(dispatchLocalDelivery).mockResolvedValue({
      ...dispatched,
    });
    render(<DeliveryConsole />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Dispatch governed local commit",
      }),
    );
    await waitFor(() =>
      expect(dispatchLocalDelivery).toHaveBeenCalledWith(authorization.id),
    );
    expect(
      await screen.findByText("Local commit created", undefined, {
        timeout: 3_000,
      }),
    ).toBeVisible();
  });
});
