import { test as base, expect } from '@playwright/test';

// Real sessions against the disposable test database, isolated for each test.
export const test = base.extend({
  context: async ({ context }, use) => {
    const response = await context.request.post('/api/auth/login', {
      data: { username: 'admin', password: 'E2e-admin-password-2026' },
    });
    expect(response.ok()).toBeTruthy();
    await use(context);
  },
  request: async ({ request }, use) => {
    const response = await request.post('/api/auth/login', {
      data: { username: 'admin', password: 'E2e-admin-password-2026' },
    });
    expect(response.ok()).toBeTruthy();
    await use(request);
  },
});
export { expect };
