import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createDeliveryAuthorization,
  decideDeliveryAuthorization,
  dispatchLocalDelivery,
  getDeliveryPreview,
  listDeliveryAuthorizations,
  listReviewPackages,
  type DeliveryAuthorization,
  type ReviewPackage,
} from "@/lib/api";
import { setTestLocale } from "@/test/setup";

import { DeliveryConsole } from "./delivery-console";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    createDeliveryAuthorization: vi.fn(),
    decideDeliveryAuthorization: vi.fn(),
    dispatchLocalDelivery: vi.fn(),
    getDeliveryPreview: vi.fn(),
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
  dispatches: [],
} satisfies DeliveryAuthorization;

const preview = {
  delivery_authorization_id: authorization.id,
  manifest: {
    manifest_version: 1 as const,
    delivery_authorization_id: authorization.id,
    workspace_id: authorization.workspace_id,
    checkpoint_id: authorization.checkpoint_id,
    checkpoint_fingerprint: authorization.checkpoint_fingerprint,
    checkpoint_diff_hash: authorization.checkpoint_diff_hash,
    source_revision: authorization.source_revision,
    branch_ref: authorization.branch_ref,
    commit_message: authorization.commit_message,
    changed_paths: ["sandbox/phase6-delivery.txt"],
    changed_file_count: 1,
    total_diff_bytes: 64,
    local_git_commit_access: true as const,
    remote_access: false as const,
    push_access: false as const,
    pull_request_access: false as const,
    tag_access: false as const,
    deployment_access: false as const,
    source_repository_write_access: false as const,
    manifest_digest: "b".repeat(64),
  },
  diff_artifact:
    "diff --git a/sandbox/phase6-delivery.txt b/sandbox/phase6-delivery.txt",
  can_dispatch: true,
  next_attempt_number: 1,
  retry_of_dispatch_id: null,
  blocking_code: null,
};

describe("DeliveryConsole", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listReviewPackages).mockResolvedValue([]);
    vi.mocked(listDeliveryAuthorizations).mockResolvedValue([]);
    vi.mocked(getDeliveryPreview).mockResolvedValue(preview);
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

  it("localizes a Chinese Delivery status and stable error while retaining its code", async () => {
    setTestLocale("zh-CN");
    vi.mocked(listDeliveryAuthorizations).mockResolvedValue([
      {
        ...authorization,
        status: "stale",
        error_code: "delivery_authorization_expired",
      },
    ]);

    render(<DeliveryConsole />);

    expect(await screen.findByText("已失效")).toBeVisible();
    expect(screen.getByText(/交付授权在派发前已过期/)).toHaveTextContent(
      "delivery_authorization_expired",
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
      screen.getByRole("button", {
        name: "Approve local commit Delivery Authorization",
      }),
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
      await screen.findByRole("button", { name: "Review delivery preview" }),
    );
    expect(
      await screen.findByText("Immutable delivery manifest · attempt 1"),
    ).toBeVisible();
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "I confirm this exact manifest digest for local-only delivery.",
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Dispatch confirmed local delivery",
      }),
    );
    await waitFor(() =>
      expect(dispatchLocalDelivery).toHaveBeenCalledWith(
        authorization.id,
        {
          confirmation_digest: preview.manifest.manifest_digest,
          retry_of_dispatch_id: null,
        },
        `delivery-dispatch-v1:${authorization.id}:1:${preview.manifest.manifest_digest}`,
      ),
    );
    expect(
      await screen.findByText("Local commit created", undefined, {
        timeout: 3_000,
      }),
    ).toBeVisible();
  });

  it("reuses the preview-scoped idempotency key after an unknown response", async () => {
    const approved = {
      ...authorization,
      status: "approved" as const,
      decided_at: "2026-07-31T08:01:00Z",
    };
    vi.mocked(listDeliveryAuthorizations).mockResolvedValue([approved]);
    vi.mocked(dispatchLocalDelivery)
      .mockRejectedValueOnce(new Error("Local response was not observed"))
      .mockResolvedValue(approved);
    render(<DeliveryConsole />);

    fireEvent.click(
      await screen.findByRole("button", { name: "Review delivery preview" }),
    );
    fireEvent.click(
      await screen.findByRole("checkbox", {
        name: "I confirm this exact manifest digest for local-only delivery.",
      }),
    );
    const dispatchButton = screen.getByRole("button", {
      name: "Dispatch confirmed local delivery",
    });
    fireEvent.click(dispatchButton);
    expect(
      await screen.findByText("An unexpected error occurred. Try again."),
    ).toBeVisible();
    fireEvent.click(dispatchButton);

    await waitFor(() => expect(dispatchLocalDelivery).toHaveBeenCalledTimes(2));
    const firstKey = vi.mocked(dispatchLocalDelivery).mock.calls[0]?.[2];
    const secondKey = vi.mocked(dispatchLocalDelivery).mock.calls[1]?.[2];
    expect(firstKey).toBe(
      `delivery-dispatch-v1:${authorization.id}:1:${preview.manifest.manifest_digest}`,
    );
    expect(secondKey).toBe(firstKey);
  });

  it("shows terminal history and confirms the exact manifest for safe retry", async () => {
    const dispatchId = "81000000-0000-4000-8000-000000000001";
    const failed = {
      ...authorization,
      status: "failed",
      decided_at: "2026-07-31T08:01:00Z",
      dispatched_at: "2026-07-31T08:02:00Z",
      terminal_at: "2026-07-31T08:02:01Z",
      error_code: "workspace_state_invalid",
      dispatches: [
        {
          id: dispatchId,
          delivery_authorization_id: authorization.id,
          attempt_number: 1,
          retry_of_dispatch_id: null,
          runner_job_id: "82000000-0000-4000-8000-000000000001",
          manifest_digest: preview.manifest.manifest_digest,
          confirmation_digest: preview.manifest.manifest_digest,
          status: "failed",
          request_id: "request-failed",
          idempotency_request_hash: "c".repeat(64),
          error_code: "workspace_state_invalid",
          created_at: "2026-07-31T08:02:00Z",
          terminal_at: "2026-07-31T08:02:01Z",
          job: {},
        },
      ],
    } as unknown as DeliveryAuthorization;
    const retryPreview = {
      ...preview,
      next_attempt_number: 2,
      retry_of_dispatch_id: dispatchId,
    };
    vi.mocked(listDeliveryAuthorizations).mockResolvedValue([failed]);
    vi.mocked(getDeliveryPreview).mockResolvedValue(retryPreview);
    vi.mocked(dispatchLocalDelivery).mockResolvedValue(failed);
    render(<DeliveryConsole />);

    const localizedErrors = await screen.findAllByText(
      /The Workspace state does not allow/,
    );
    expect(localizedErrors).toHaveLength(2);
    expect(localizedErrors[1]).toHaveTextContent("workspace_state_invalid");
    expect(localizedErrors[1]).toHaveTextContent("request-failed");
    fireEvent.click(screen.getByRole("button", { name: "Review safe retry" }));
    expect(
      await screen.findByText("Immutable delivery manifest · attempt 2"),
    ).toBeVisible();
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "I confirm this exact manifest digest for local-only delivery.",
      }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Retry exact local delivery" }),
    );
    await waitFor(() =>
      expect(dispatchLocalDelivery).toHaveBeenCalledWith(
        authorization.id,
        {
          confirmation_digest: preview.manifest.manifest_digest,
          retry_of_dispatch_id: dispatchId,
        },
        `delivery-dispatch-v1:${authorization.id}:2:${preview.manifest.manifest_digest}`,
      ),
    );
  });
});
