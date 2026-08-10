import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  outputDir: '../artifacts/test-results/playwright',
  reporter: [['html', { open: 'never', outputFolder: '../artifacts/playwright-report' }], ['list']],
  use: {
    baseURL: 'http://127.0.0.1:15176',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    launchOptions: { executablePath: '/usr/bin/google-chrome' },
  },
  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: /(responsive|video-demo)\.spec\.ts/,
    },
    {
      name: 'tablet',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1024, height: 1366 } },
      testMatch: /responsive\.spec\.ts/,
    },
    {
      name: 'mobile-smoke',
      use: { ...devices['Desktop Chrome'], viewport: { width: 393, height: 851 } },
      testMatch: /responsive\.spec\.ts/,
    },
  ],
  webServer: [
    {
      command:
        'GEOFORGE_DATABASE_URL=sqlite:///../artifacts/test-results/geoforge-e2e.db ' +
        'GEOFORGE_DATA_DIR=../artifacts/test-results/e2e-data ' +
        'GEOFORGE_ARTIFACT_DIR=../artifacts/test-results/e2e-runs ' +
        `GEOFORGE_ALLOWED_ORIGINS='["http://127.0.0.1:15176"]' ` +
        '../.venv/bin/uvicorn geoforge.main:app --app-dir ../backend --host 127.0.0.1 --port 18083',
      url: 'http://127.0.0.1:18083/api/health',
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command:
        'VITE_API_URL=http://127.0.0.1:18083/api npm run dev -- --host 127.0.0.1 --port 15176',
      url: 'http://127.0.0.1:15176',
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})
