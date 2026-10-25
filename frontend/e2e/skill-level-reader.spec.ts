import { expect, test } from './fixtures';

test('employee can open every competency level from its name without editing access', async ({
  browser,
  request,
}) => {
  const employee = (await (await request.get('/api/employees?q=anna.morozova@example.com')).json())
    .items[0];
  const response = await request.post('/api/skills', {
    data: {
      name: 'Excel требования E2E',
      category: 'Технические',
      scale: {
        type: 'numeric',
        min: 0,
        max: 2,
        names: { '0': 'Нет опыта', '1': 'Базовый', '2': 'Продвинутый' },
        descriptions: {
          '0': 'Ещё не работал с таблицами.',
          '1': 'Создаёт таблицы и использует простые формулы.',
          '2': 'Строит сводные таблицы.\nАвтоматизирует отчёты.',
        },
      },
    },
  });
  expect(response.status()).toBe(201);
  const skill = await response.json();
  const path = `/api/employees/${employee.id}/skills/${skill.id}`;
  expect((await request.put(path, { data: { current_level: 1, target_level: 2 } })).status()).toBe(
    200,
  );
  const accountResponse = await request.post('/api/accounts', {
    data: {
      username: 'level_reader_e2e',
      password: 'Level-reader-password-2026',
      role: 'employee',
      employee_id: employee.id,
    },
  });
  expect(accountResponse.status()).toBe(201);
  const account = await accountResponse.json();
  const reader = await browser.newContext({
    baseURL: 'http://127.0.0.1:5174',
    viewport: { width: 390, height: 844 },
    extraHTTPHeaders: { 'X-HRM-Request': '1' },
  });
  try {
    expect(
      (
        await reader.request.post('/api/auth/login', {
          data: { username: 'level_reader_e2e', password: 'Level-reader-password-2026' },
        })
      ).status(),
    ).toBe(200);
    const page = await reader.newPage();
    await page.goto(`/employees/${employee.id}`);
    const current = page.getByRole('button', {
      name: 'Текущий уровень Excel требования E2E: 1 — Базовый',
      exact: true,
    });
    await expect(current).toHaveText('1 — Базовый');
    await current.focus();
    await current.press('Enter');
    const dialog = page.getByRole('dialog');
    await expect(
      dialog.getByRole('heading', {
        name: 'Excel требования E2E: уровни компетенции',
        exact: true,
      }),
    ).toBeVisible();
    await expect(dialog.locator('.skill-level-reference > li')).toHaveCount(3);
    for (const name of ['Нет опыта', 'Базовый', 'Продвинутый'])
      await expect(dialog.getByRole('heading', { name, exact: true })).toBeVisible();
    await expect(dialog).toContainText('Создаёт таблицы и использует простые формулы.');
    await expect(dialog).toContainText('Автоматизирует отчёты.');
    await expect(dialog.locator('.is-current-level')).toContainText('Базовый');
    await expect(dialog.getByRole('textbox')).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      390,
    );
    await page.screenshot({ path: '../artifacts/skill-level-reader-mobile.png' });
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
    await expect(current).toBeFocused();
    // Unassessed employees can still read all levels through their target, including zero.
    expect(
      (await request.put(path, { data: { current_level: null, target_level: 0 } })).status(),
    ).toBe(200);
    await page.reload();
    await page
      .getByRole('button', {
        name: 'Целевой уровень Excel требования E2E: 0 — Нет опыта',
        exact: true,
      })
      .click();
    await expect(dialog.locator('.skill-level-reference > li')).toHaveCount(3);
    await expect(dialog.locator('.is-current-level')).toHaveCount(0);
    await expect(dialog.locator('.skill-level-reference > li').first()).toContainText(
      'Целевой уровень',
    );
    const forbidden = await reader.request.put(`/api/skills/${skill.id}`, {
      data: { ...skill, scale: { ...skill.scale, names: { '1': 'Самовольное изменение' } } },
    });
    expect(forbidden.status()).toBe(403);
  } finally {
    await reader.close();
    await request.delete(path);
    await request.delete(`/api/skills/${skill.id}`);
    await request.put(`/api/accounts/${account.id}`, {
      data: {
        username: account.username,
        role: 'employee',
        employee_id: employee.id,
        is_active: false,
      },
    });
  }
});
