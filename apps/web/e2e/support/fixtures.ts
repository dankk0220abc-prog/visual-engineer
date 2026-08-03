import { expect, test as base } from "@playwright/test";

import { E2eTestResources } from "./isolation";

export const test = base.extend<{ resources: E2eTestResources }>({
  resources: async ({ request }, provide) => {
    const resources = new E2eTestResources(request);
    try {
      await provide(resources);
    } finally {
      await resources.cleanup();
    }
  },
});

export { expect };
