import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  timeout: 60000,
  expect: { timeout: 15000 },
  use: {
    baseURL: "http://127.0.0.1:8000",
    headless: true,
    viewport: { width: 1440, height: 1000 },
  },
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile: new URL("../outputs/browser-tests.json", import.meta.url)
          .pathname,
      },
    ],
  ],
});
