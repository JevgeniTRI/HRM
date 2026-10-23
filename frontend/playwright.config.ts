import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  use: {
    baseURL: 'http://127.0.0.1:5174',
    browserName: 'chromium',
    extraHTTPHeaders: { 'X-HRM-Request': '1' },
    trace: 'retain-on-failure',
    viewport: { width: 1440, height: 1080 },
  },
  reporter: 'list',
  webServer: [
    {
      command: '..\\backend\\.venv\\Scripts\\python.exe ..\\backend\\tests\\run_e2e_server.py',
      url: 'http://127.0.0.1:8001/api/health',
      timeout: 30_000,
      reuseExistingServer: false,
    },
    {
      command:
        'node node_modules/vite/bin/vite.js --host 127.0.0.1 --configLoader native --port 5174',
      url: 'http://127.0.0.1:5174',
      timeout: 30_000,
      reuseExistingServer: false,
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8001' },
    },
  ],
});
