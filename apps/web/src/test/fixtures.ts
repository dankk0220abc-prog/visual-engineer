import type { Task } from "@/lib/api";

export function taskFixture(overrides: Partial<Task> = {}): Task {
  return {
    id: "9dbe3a52-3db5-4d10-bbfb-94f15f6fe4bc",
    title: "Improve navigation",
    objective: "Make primary navigation easier to understand.",
    repository_kind: "local_path",
    repository_display_name: "design-system",
    repository_locator: "/workspace/design-system",
    status: "draft",
    version: 1,
    created_at: "2026-07-26T03:00:00Z",
    updated_at: "2026-07-26T03:00:00Z",
    ...overrides,
  } as Task;
}
