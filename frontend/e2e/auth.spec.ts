import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

const password = 'Browser-role-password-2026';
let people: { id: number; first_name: string; last_name: string; department_id: number }[];
let accounts: {
  id: number;
  username: string;
  role: string;
  employee_id: number;
  is_active: boolean;
}[];

async function signIn(page: Page, username: string, value = password) {
  await page.goto('/');
  await page.getByLabel('Логин', { exact: true }).fill(username);
  await page.getByLabel('Пароль', { exact: true }).fill(value);
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Выйти', exact: true })).toBeVisible();
}

test.beforeAll(async ({ request }) => {
  expect(
    (
      await request.post('/api/auth/login', {
        data: { username: 'admin', password: 'E2e-admin-password-2026' },
      })
    ).ok(),
  ).toBeTruthy();
  const all = (await (await request.get('/api/employees?page_size=100')).json())
    .items as typeof people;
  const department = all[0].department_id;
  const own = all.filter((person) => person.department_id === department);
  // Find a department with at least three seeded employees, preserving dashboard totals.
  const members =
    own.length >= 3
      ? own
      : all.filter(
          (person) =>
            person.department_id ===
            all.find(
              (candidate) =>
                all.filter((p) => p.department_id === candidate.department_id).length >= 3,
            )!.department_id,
        );
  people = [
    ...members.slice(0, 3),
    all.find((person) => person.department_id !== members[0].department_id)!,
  ];
  accounts = [];
  const existing = await (await request.get('/api/accounts')).json();
  for (const [index, role] of ['employee', 'manager', 'manager', 'power_user'].entries()) {
    const found = existing.find(
      (account: { username: string }) => account.username === `browser-${index}`,
    );
    if (found) {
      accounts.push(found);
      continue;
    }
    const response = await request.post('/api/accounts', {
      data: { username: `browser-${index}`, password, role, employee_id: people[index].id },
    });
    expect(response.status()).toBe(201);
    accounts.push(await response.json());
  }
});

test('login errors, administrator account controls and logout', async ({ page }) => {
  await page.goto('/accounts');
  await expect(page.getByRole('heading', { name: 'Вход в рабочее пространство' })).toBeVisible();
  await page.getByLabel('Логин', { exact: true }).fill('admin');
  await page.getByLabel('Пароль', { exact: true }).fill('wrong');
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByText('Неверный логин или пароль', { exact: true })).toBeVisible();
  await page.getByLabel('Пароль', { exact: true }).fill('E2e-admin-password-2026');
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await page.getByRole('navigation').getByRole('link', { name: 'Аккаунты и доступ' }).click();
  await expect(page.getByRole('heading', { name: 'Аккаунты и доступ', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Создать аккаунт', exact: true }).click();
  await expect(
    page.getByRole('dialog').getByRole('combobox', { name: 'Роль', exact: true }),
  ).toBeVisible();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Логин', { exact: true }).fill('browser-ui-admin');
  await dialog.getByRole('combobox', { name: 'Роль', exact: true }).selectOption('admin');
  await dialog.getByLabel('Начальный пароль', { exact: false }).fill(password);
  await dialog.getByRole('button', { name: 'Создать аккаунт', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole('cell', { name: 'browser-ui-admin', exact: true })).toBeVisible();
  await page
    .getByRole('button', { name: 'Редактировать аккаунт browser-ui-admin', exact: true })
    .click();
  await dialog.getByRole('checkbox', { name: 'Аккаунт активен', exact: true }).uncheck();
  await dialog.getByRole('button', { name: 'Сохранить', exact: true }).click();
  await expect(
    page
      .getByRole('row')
      .filter({ has: page.getByRole('cell', { name: 'browser-ui-admin', exact: true }) }),
  ).toContainText('Отключён');
  await page.screenshot({ path: '../artifacts/auth-accounts.png', fullPage: true });
  await page.getByRole('button', { name: 'Выйти', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Вход в рабочее пространство' })).toBeVisible();
  await page.goto('/employees');
  await expect(page.getByRole('heading', { name: 'Вход в рабочее пространство' })).toBeVisible();
});

test('employee sees their resume and tasks, edits resume and cannot open their manager', async ({
  page,
  request,
}) => {
  await request.post('/api/auth/login', {
    data: { username: 'admin', password: 'E2e-admin-password-2026' },
  });
  const task = await (
    await request.post('/api/tasks', {
      data: { title: 'Личная задача авторизации', assignee_id: people[0].id },
    })
  ).json();
  try {
    await signIn(page, 'browser-0');
    await expect(page).toHaveURL(`/employees/${people[0].id}`);
    const navigation = page.getByRole('navigation');
    await expect(navigation.getByRole('link', { name: 'Моя карточка-резюме' })).toBeVisible();
    await expect(navigation.getByRole('link', { name: 'Сотрудники', exact: true })).toHaveCount(0);
    await expect(navigation.getByRole('link', { name: 'Аккаунты и доступ' })).toHaveCount(0);
    await page.getByRole('button', { name: 'Редактировать', exact: true }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByLabel('Должность', { exact: true })).toBeDisabled();
    await expect(
      dialog.getByRole('combobox', { name: 'Подразделение', exact: true }),
    ).toBeDisabled();
    await dialog.getByLabel('О себе', { exact: true }).fill('Развиваю профессиональные навыки.');
    await dialog.getByRole('button', { name: 'Сохранить', exact: true }).click();
    await expect(
      page.getByText('Развиваю профессиональные навыки.', { exact: true }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByText('Развиваю профессиональные навыки.', { exact: true }),
    ).toBeVisible();
    await navigation.getByRole('link', { name: 'Мои задачи', exact: true }).click();
    await expect(
      page.getByRole('article', { name: 'Задача: Личная задача авторизации', exact: true }),
    ).toBeVisible();
    await expect(page.getByRole('article')).toHaveCount(1);
    await expect(
      page.getByRole('button', { name: 'Удалить задачу Личная задача авторизации' }),
    ).toHaveCount(0);
    await page.screenshot({ path: '../artifacts/auth-employee.png', fullPage: true });
    await page.goto(`/employees/${people[1].id}`);
    await expect(page.getByText('Сотрудник не найден', { exact: true })).toBeVisible();
    await page.goto('/accounts');
    await expect(page).toHaveURL(`/employees/${people[0].id}`);
  } finally {
    await request.delete(`/api/tasks/${task.id}?version=1`);
  }
});

test('manager sees only their department and can edit a peer manager', async ({ page }) => {
  await signIn(page, 'browser-1');
  await page.getByRole('navigation').getByRole('link', { name: 'Мой отдел', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Мой отдел', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Добавить сотрудника', exact: true })).toHaveCount(
    0,
  );
  await expect(page.locator('tbody')).not.toContainText(
    `${people[3].first_name} ${people[3].last_name}`,
  );
  await page.goto(`/employees/${people[2].id}`);
  await page.getByRole('button', { name: 'Редактировать', exact: true }).click();
  await expect(page.getByRole('dialog').getByLabel('Должность', { exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Отмена', exact: true }).click();
  await page.goto(`/employees/${people[3].id}`);
  await expect(page.getByText('Сотрудник не найден', { exact: true })).toBeVisible();
});

test('power user sees all departments without account administration', async ({ page }) => {
  await signIn(page, 'browser-3');
  const navigation = page.getByRole('navigation');
  await expect(navigation.getByRole('link', { name: 'Аккаунты и доступ' })).toHaveCount(0);
  await navigation.getByRole('link', { name: 'Подразделения', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Подразделения', exact: true })).toBeVisible();
  const response = await page.request.get('/api/accounts');
  expect(response.status()).toBe(403);
  await page.goto(`/employees/${people[0].id}`);
  await expect(page.getByRole('button', { name: 'Редактировать', exact: true })).toBeVisible();
});

test('disabling an account ends its browser session', async ({ page, request }) => {
  await request.post('/api/auth/login', {
    data: { username: 'admin', password: 'E2e-admin-password-2026' },
  });
  await signIn(page, 'browser-0');
  const response = await request.put(`/api/accounts/${accounts[0].id}`, {
    data: { ...accounts[0], is_active: false },
  });
  expect(response.ok()).toBeTruthy();
  await page.getByRole('navigation').getByRole('link', { name: 'Мои задачи' }).click();
  await expect(page.getByRole('heading', { name: 'Вход в рабочее пространство' })).toBeVisible();
});
