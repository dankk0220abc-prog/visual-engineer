import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listAIProviders } from "@/lib/api";
import { aiProviderFixtures } from "@/test/fixtures";
import { setTestLocale } from "@/test/setup";

import { ProviderSelector, ProviderStatusConsole } from "./provider-foundation";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listAIProviders: vi.fn() };
});

const mockedListAIProviders = vi.mocked(listAIProviders);

beforeEach(() => {
  vi.clearAllMocks();
  mockedListAIProviders.mockResolvedValue(aiProviderFixtures());
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
        "Disabled because the required local API key is not configured.",
      ),
    ).toHaveLength(5);
    expect(
      screen.getAllByText("Live provider validation not performed"),
    ).toHaveLength(5);

    await user.click(fixture);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("renders the closed registry and explicit authority boundaries in English", async () => {
    render(<ProviderStatusConsole />);

    expect(
      screen.getByText("Loading the closed provider registry…"),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "AI Provider Foundation" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("6 providers")).toBeInTheDocument();
    expect(screen.getByText("Deterministic Fixture")).toBeInTheDocument();
    expect(screen.getByText("Zhipu GLM · 智谱 GLM")).toBeInTheDocument();
    expect(
      screen.getByText(/cannot issue an Execution Grant/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Fixture / Mock Evidence · Not a live-provider call"),
    ).toBeInTheDocument();
  });

  it("renders the same provider state in zh-CN", async () => {
    setTestLocale("zh-CN");
    render(<ProviderStatusConsole />);

    expect(
      await screen.findByRole("heading", { name: "AI Provider 基础层" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("共 6 个 Provider")).toBeInTheDocument();
    expect(
      screen.getByText("Fixture / Mock 证据 · 非真实 Provider 调用"),
    ).toBeInTheDocument();
    await waitFor(() => expect(mockedListAIProviders).toHaveBeenCalledOnce());
  });
});
