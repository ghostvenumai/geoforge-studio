import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  testMatch: /video-demo\.spec\.ts/,
  timeout: 210_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  outputDir: '../video/tmp/playwright-results',
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:15175',
    viewport: { width: 1920, height: 1080 },
    colorScheme: 'light',
    video: { mode: 'on', size: { width: 1920, height: 1080 } },
    launchOptions: { executablePath: '/usr/bin/google-chrome' },
  },
  webServer: [
    {
      command:
        'GEOFORGE_DATABASE_URL=sqlite:///../video/tmp/geoforge-video.db ' +
        'GEOFORGE_DATA_DIR=../video/tmp/data ' +
        'GEOFORGE_ARTIFACT_DIR=../video/tmp/runs ' +
        `GEOFORGE_ALLOWED_ORIGINS='["http://127.0.0.1:15175"]' ` +
        '../.venv/bin/uvicorn geoforge.main:app --app-dir ../backend --host 127.0.0.1 --port 18082',
      url: 'http://127.0.0.1:18082/api/health',
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command:
        'VITE_API_URL=http://127.0.0.1:18082/api npm run dev -- --host 127.0.0.1 --port 15175',
      url: 'http://127.0.0.1:15175',
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})
