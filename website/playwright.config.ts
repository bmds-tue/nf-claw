import { defineConfig } from "@playwright/test";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "/nf-claw";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  workers: process.env.CI ? 2 : 2,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://127.0.0.1:4177${basePath}/`,
    reducedMotion: "reduce",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { browserName: "chromium", viewport: { width: 1440, height: 1000 } } },
    { name: "mobile", use: { browserName: "chromium", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  webServer: {
    command: "node scripts/serve-export.mjs",
    url: `http://127.0.0.1:4177${basePath}/`,
    env: { TEST_BASE_PATH: basePath },
    reuseExistingServer: false,
  },
});
