import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  connectAIProviderCredential,
  getLiveProviderEvidence,
  listAIProviders,
  listLiveProviderEvidence,
  type LiveProviderEvidenceDetail,
} from "@/lib/api";
import { aiProviderFixtures } from "@/test/fixtures";
import { setTestLocale } from "@/test/setup";

import { ProviderSelector, ProviderStatusConsole } from "./provider-foundation";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listAIProviders: vi.fn(),
    listLiveProviderEvidence: vi.fn(),
    getLiveProviderEvidence: vi.fn(),
    connectAIProviderCredential: vi.fn(),
  };
});

const mockedListAIProviders = vi.mocked(listAIProviders);
const mockedListLiveProviderEvidence = vi.mocked(listLiveProviderEvidence);
const mockedGetLiveProviderEvidence = vi.mocked(getLiveProviderEvidence);
const mockedConnectCredential = vi.mocked(connectAIProviderCredential);

const liveEvidence = {
  correlation: "3a9c354f7a58",
  provider_id: "zhipu",
  classification: "live",
  lifecycle: "succeeded",
  requested_model_id: "glm-5.2",
  effective_model_status: "reported",
  effective_model_id: "glm-5.2",
  usage_status: "reported_complete",
  input_tokens: 1362,
  output_tokens: 654,
  total_tokens: 2016,
  provider_elapsed_ms: 11543,
  client_total_elapsed_ms: 11553,
  billing_status: "live_billing_unknown",
  cost_amount: null,
  cost_currency: null,
  upstream_request_id_status: "reported",
  upstream_request_fingerprint: "1".repeat(24),
  request_digest: "2".repeat(64),
  response_digest: "3".repeat(64),
  completed_at: "2026-08-10T13:28:17.504281Z",
  plan_summary: "Create one typed responsive TaskCard proposal.",
  operations: [
    { kind: "workspace_text_create_v1", target: "src/TaskCard.tsx" },
  ],
  evaluations: [
    { eval_id: "schema_validity", passed: true, summary: "Schema passed." },
  ],
  task_classification: "live_canary",
  public_task_context: "Synthetic public Provider verification context",
  governance: {
    ai_plan_status: "generated",
    approval_status: "not_decided",
    execution_grant_status: "not_issued",
    runner_authority: "not_granted",
    review_status: "not_created",
    delivery_status: "not_created",
  },
} satisfies LiveProviderEvidenceDetail;

beforeEach(() => {
  vi.clearAllMocks();
  mockedListAIProviders.mockResolvedValue(aiProviderFixtures());
  mockedListLiveProviderEvidence.mockResolvedValue([]);
  mockedGetLiveProviderEvidence.mockResolvedValue(liveEvidence);
  mockedConnectCredential.mockResolvedValue({
    provider_id: "zhipu",
    connected: true,
    persistence: "process_memory_only",
    expires_at: "2026-08-10T14:28:17.504281Z",
  });
});

describe("Provider foundation", () => {
  it("keeps fixture selectable and every real provider visibly disabled", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    render(
      <ProviderSelector
        providers={aiProviderFixtures()}
        value="deterministic-fixture"
        onChange={onChange}
      />,
    );

    const fixture = screen.getByRole("radio", {
      name: "Select Deterministic Fixture",
    });
    expect(fixture).toBeEnabled();
    expect(fixture).toBeChecked();
    expect(screen.getAllByRole("radio")).toHaveLength(6);
    for (const name of [
      "Zhipu GLM · 智谱 GLM",
      "Qwen · 通义千问",
      "DeepSeek",
      "Doubao · 豆包",
      "Kimi",
    ]) {
      expect(
        screen.getByRole("radio", { name: `Select ${name}` }),
      ).toBeDisabled();
    }
    expect(
      screen.getAllByText(
        "Adapter is supported; connect your key to use it in this session.",
      ),
    ).toHaveLength(5);
    expect(
      screen.getByText("Fixture / Mock Evidence · Not a live-provider call"),
    ).toBeInTheDocument();

    await user.click(fixture);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("renders the closed registry and explicit authority boundaries in English", async () => {
    render(<ProviderStatusConsole />);

    expect(
      screen.getByText("Loading Provider status and safe live Evidence…"),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", {
        name: "AI Provider & Live Evidence",
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("6 providers")).toBeInTheDocument();
    expect(screen.getByText("Deterministic Fixture")).toBeInTheDocument();
    expect(screen.getAllByText("Zhipu GLM · 智谱 GLM")).toHaveLength(2);
    expect(
      screen.getByText(/cannot issue an Execution Grant/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Fixture / Mock Evidence · Not a live-provider call"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No successful live Evidence yet"),
    ).toBeInTheDocument();
  });

  it("renders the same provider state in zh-CN", async () => {
    setTestLocale("zh-CN");
    render(<ProviderStatusConsole />);

    expect(
      await screen.findByRole("heading", { name: "AI Provider 与真实证据" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("共 6 个 Provider")).toBeInTheDocument();
    expect(screen.getByText("暂无成功的真实调用证据")).toBeInTheDocument();
    expect(
      screen.getByText("Fixture / Mock 证据 · 非真实 Provider 调用"),
    ).toBeInTheDocument();
    await waitFor(() => expect(mockedListAIProviders).toHaveBeenCalledOnce());
  });

  it("keeps the fixture disclosure visible in the zh-CN Provider Selector", () => {
    setTestLocale("zh-CN");
    render(
      <ProviderSelector
        providers={aiProviderFixtures()}
        value="deterministic-fixture"
        onChange={vi.fn()}
      />,
    );

    expect(
      screen.getByText("Fixture / Mock 证据 · 非真实 Provider 调用"),
    ).toBeInTheDocument();
  });

  it("connects a BYOK credential without redisplaying it", async () => {
    const user = userEvent.setup();
    render(<ProviderStatusConsole />);
    await screen.findByText("6 providers");

    await user.click(
      screen.getAllByRole("button", { name: "Connect your key" })[0],
    );
    const input = screen.getByLabelText("API key");
    await user.type(input, "synthetic-user-key");
    await user.click(screen.getByRole("button", { name: "Connect" }));

    await waitFor(() =>
      expect(mockedConnectCredential).toHaveBeenCalledWith(
        "zhipu",
        "synthetic-user-key",
      ),
    );
    expect(input).toHaveValue("");
    expect(screen.queryByText("synthetic-user-key")).not.toBeInTheDocument();
  });

  it("opens the typed safe projection for successful live Evidence", async () => {
    const user = userEvent.setup();
    mockedListLiveProviderEvidence.mockResolvedValue([liveEvidence]);
    render(<ProviderStatusConsole />);

    await user.click(
      await screen.findByRole("button", { name: "View Evidence" }),
    );

    expect(await screen.findByText("Typed Plan")).toBeInTheDocument();
    expect(screen.getByText("Provider audit")).toBeInTheDocument();
    expect(screen.getByText("Governance boundary")).toBeInTheDocument();
    expect(screen.getByText("Not granted")).toBeInTheDocument();
    expect(mockedGetLiveProviderEvidence).toHaveBeenCalledWith("3a9c354f7a58");
  });
});
