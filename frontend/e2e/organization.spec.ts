import { expect, test } from './fixtures';
import type { Page } from '@playwright/test';

const password = 'Organization-browser-2026';
let people: { id: number; first_name: string; last_name: string }[] = [];

async function signIn(page: Page, username: string) {
  await page.getByRole('button', { name: 'Выйти', exact: true }).click();
  await page.getByLabel('Логин', { exact: true }).fill(username);
  await page.getByLabel('Пароль', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Выйти', exact: true })).toBeVisible();
}

test.beforeAll(async ({ request }) => {
  const departments = await (await request.get('/api/departments')).json();
  for (const [index, name] of ['Директор', 'Руководитель', 'Специалист', 'Координатор'].entries()) {
    const response = await request.post('/api/employees', {
      data: {
        first_name: name,
        last_name: 'Иерархия',
        email: `org-browser-${index}@example.com`,
        position: name,
        department_id: departments[index === 3 ? 1 : 0].id,
        hired_at: '2026-01-01',
      },
    });
    expect(response.status()).toBe(201);
    const person = await response.json();
    people.push(person);
    const account = await request.post('/api/accounts', {
      data: {
        username: `org-browser-${index}`,
        password,
        employee_id: person.id,
        role: index === 3 ? 'power_user' : 'employee',
      },
    });
    expect(account.status()).toBe(201);
  }
});

test.afterAll(async ({ request }) => {
  const accounts = await (await request.get('/api/accounts')).json();
  for (const account of accounts.filter((a: { username: string }) =>
    a.username.startsWith('org-browser-'),
  )) {
    expect(
      (
        await request.put(`/api/accounts/${account.id}`, {
          data: { ...account, role: 'admin', employee_id: null, is_active: false },
        })
      ).ok(),
    ).toBeTruthy();
  }
  for (const index of [2, 1, 0, 3]) {
    if (people[index])
      expect((await request.delete(`/api/employees/${people[index].id}`)).status()).toBe(204);
  }
});

test('administrator and power user configure department roles; empty managers become employees', async ({
  page,
}) => {
  await page.goto(`/employees/${people[0].id}`);
  await page.getByRole('button', { name: 'Настроить подчинённость', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('combobox', { name: 'Роль в отделе' }).selectOption('head');
  await dialog.getByRole('checkbox', { name: /^Руководитель Иерархия/ }).check();
  await expect(dialog.getByRole('checkbox', { name: /^Координатор Иерархия/ })).toHaveCount(0);
  await dialog.getByRole('button', { name: 'Сохранить подчинённость' }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole('region', { name: 'Руководитель и подчинённые' })).toContainText(
    'Руководитель отдела',
  );
  await signIn(page, 'org-browser-3');
  for (const [index, parentIndex, kind] of [
    [1, 0, 'intermediate'],
    [2, 1, 'employee'],
  ] as const) {
    await page.goto(`/employees/${people[index].id}`);
    await page.getByRole('button', { name: 'Настроить подчинённость', exact: true }).click();
    await dialog.getByRole('combobox', { name: 'Роль в отделе' }).selectOption(kind);
    if (kind === 'intermediate')
      await dialog.getByRole('checkbox', { name: /^Специалист Иерархия/ }).check();
    const managers = dialog.getByRole('combobox', { name: 'Непосредственный руководитель' });
    await expect(managers.locator(`option[value="${people[parentIndex].id}"]`)).toBeAttached();
    await managers.selectOption(String(people[parentIndex].id));
    await dialog.getByRole('button', { name: 'Сохранить подчинённость' }).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByRole('region', { name: 'Руководитель и подчинённые' })).toContainText(
      `${people[parentIndex].first_name} Иерархия`,
    );
  }
  // The director cannot report to their own subordinate.
  await page.goto(`/employees/${people[0].id}`);
  await page.getByRole('button', { name: 'Настроить подчинённость', exact: true }).click();
  await dialog.getByRole('combobox', { name: 'Роль в отделе' }).selectOption('intermediate');
  await dialog
    .getByRole('combobox', { name: 'Непосредственный руководитель' })
    .selectOption(String(people[1].id));
  await dialog.getByRole('button', { name: 'Сохранить подчинённость' }).click();
  await expect(dialog.getByRole('alert')).toContainText('Нельзя создать цикл');
  await dialog.getByRole('button', { name: 'Отмена', exact: true }).click();
  await page.screenshot({ path: '../artifacts/organization-hierarchy.png', fullPage: true });
  await signIn(page, 'org-browser-0');
  await page
    .getByRole('navigation')
    .getByRole('link', { name: 'Моя команда', exact: true })
    .click();
  await expect(page.locator('tbody tr')).toHaveCount(3);
  await expect(page.locator('tbody')).toContainText('Специалист Иерархия');
  await expect(page.locator('tbody')).not.toContainText('Координатор Иерархия');
  await page.goto(`/employees/${people[1].id}`);
  const organization = page.getByRole('region', { name: 'Руководитель и подчинённые' });
  await expect(
    organization.getByRole('link', { name: 'Специалист Иерархия', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Настроить подчинённость', exact: true }),
  ).toHaveCount(0);
  await signIn(page, 'org-browser-2');
  await expect(page).toHaveURL(`/employees/${people[2].id}`);
  await expect(organization).toContainText('Руководитель Иерархия');
  await expect(organization.getByRole('link')).toHaveCount(0);
  expect((await page.request.get(`/api/employees/${people[0].id}`)).status()).toBe(404);
  await signIn(page, 'org-browser-3');
  const forbidden = await page.request.put(`/api/employees/${people[2].id}/organization`, {
    data: {
      kind: 'employee',
      manager_id: people[3].id,
    },
  });
  expect(forbidden.status()).toBe(422);
  await page.goto(`/employees/${people[2].id}`);
  await page.getByRole('button', { name: 'Настроить подчинённость', exact: true }).click();
  await dialog
    .getByRole('combobox', { name: 'Непосредственный руководитель' })
    .selectOption(String(people[0].id));
  await dialog.getByRole('button', { name: 'Сохранить подчинённость' }).click();
  await expect(dialog).not.toBeVisible();
  await page.goto(`/employees/${people[1].id}`);
  await expect(organization).toContainText('Сотрудник ·');
  await expect(organization.getByText('Прямые подчинённые')).toHaveCount(0);
  await signIn(page, 'org-browser-1');
  await expect(page).toHaveURL(`/employees/${people[1].id}`);
  await expect(
    page.getByRole('navigation').getByRole('link', { name: 'Моя команда', exact: true }),
  ).toHaveCount(0);
});
