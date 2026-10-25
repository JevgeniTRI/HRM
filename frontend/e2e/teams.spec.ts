import { expect, test } from './fixtures';

let departmentId: number;
let teamId: number;
let people: { id: number; first_name: string }[] = [];

test.describe.configure({ mode: 'serial' });
test.beforeAll(async ({ request }) => {
  const department = await request.post('/api/departments', {
    data: { name: 'Команды для браузерной проверки' },
  });
  expect(department.status()).toBe(201);
  departmentId = (await department.json()).id;
  for (const [index, name] of [
    'Начальник',
    'Прежний',
    'Новый',
    'Первый',
    'Второй',
    'Третий',
  ].entries()) {
    const response = await request.post('/api/employees', {
      data: {
        first_name: name,
        last_name: 'Команда',
        email: `team-browser-${index}@example.com`,
        position: index > 2 ? 'BulkRole' : 'Leader',
        department_id: departmentId,
        hired_at: '2026-01-01',
      },
    });
    expect(response.status()).toBe(201);
    people.push(await response.json());
  }
});
test.afterAll(async ({ request }) => {
  const teams = await (await request.get(`/api/teams?department_id=${departmentId}`)).json();
  for (const team of teams) {
    const members = await (await request.get(`/api/teams/${team.id}/members?page_size=100`)).json();
    for (const person of members.items) {
      const current = await (await request.get(`/api/teams/${team.id}`)).json();
      expect(
        (
          await request.delete(
            `/api/teams/${team.id}/members/${person.id}?version=${current.version}`,
          )
        ).status(),
      ).toBe(204);
    }
    const current = await (await request.get(`/api/teams/${team.id}`)).json();
    expect(
      (await request.delete(`/api/teams/${team.id}?version=${current.version}`)).status(),
    ).toBe(204);
  }
  const all = await (
    await request.get(`/api/employees?department_id=${departmentId}&page_size=100`)
  ).json();
  const remaining = new Set<number>(all.items.map((person: { id: number }) => person.id));
  for (let pass = 0; pass < all.total && remaining.size; pass++) {
    for (const id of [...remaining])
      if ((await request.delete(`/api/employees/${id}`)).status() === 204) remaining.delete(id);
  }
  expect(remaining.size).toBe(0);
  expect((await request.delete(`/api/departments/${departmentId}`)).status()).toBe(204);
});

test('create a team, select all matching employees and replace its manager', async ({
  page,
  request,
}) => {
  await page.goto('/teams');
  await page.getByRole('button', { name: 'Создать команду', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Название команды', { exact: true }).fill('Браузерная команда');
  await dialog.getByLabel('Код команды', { exact: true }).fill('BROWSER-TEAM');
  await dialog
    .getByRole('combobox', { name: 'Отдел', exact: true })
    .selectOption(String(departmentId));
  await dialog
    .getByRole('combobox', { name: 'Руководитель команды', exact: true })
    .selectOption(String(people[1].id));
  await dialog
    .getByRole('combobox', { name: 'Вышестоящий руководитель', exact: true })
    .selectOption(String(people[0].id));
  await dialog.getByRole('button', { name: 'Создать команду', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Браузерная команда', exact: true }),
  ).toBeVisible();
  teamId = Number(new URL(page.url()).pathname.split('/').pop());
  await page.getByRole('button', { name: 'Добавить сотрудников', exact: true }).click();
  await dialog.getByRole('searchbox', { name: 'Поиск сотрудников', exact: true }).fill('BulkRole');
  await dialog.getByRole('button', { name: 'Выбрать всех найденных (3)', exact: true }).click();
  await expect(dialog.getByText('Выбрано: 3', { exact: true })).toBeVisible();
  await dialog.getByRole('button', { name: 'Назначить выбранных (3)', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(3);
  await page.getByRole('button', { name: 'Заменить руководителя', exact: true }).click();
  await dialog
    .getByRole('combobox', { name: 'Новый руководитель', exact: true })
    .selectOption(String(people[2].id));
  await dialog.getByRole('button', { name: 'Заменить и передать команду', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole('region', { name: 'Руководство команды' })).toContainText(
    'Новый Команда',
  );
  await expect(page.locator('tbody tr')).toHaveCount(3);
  const old = await (await request.get(`/api/employees/${people[1].id}`)).json();
  expect(old.organization_role).toBe('employee');
  const members = await (await request.get(`/api/teams/${teamId}/members`)).json();
  expect(
    members.items.every((person: { manager_id: number }) => person.manager_id === people[2].id),
  ).toBeTruthy();
  await page.screenshot({ path: '../artifacts/teams-replacement.png', fullPage: true });
});

test('CSV preview creates nothing until confirmation and shows row errors', async ({
  page,
  request,
}) => {
  await page.goto('/teams');
  await page.getByRole('button', { name: 'Импорт Excel / CSV', exact: true }).click();
  const dialog = page.getByRole('dialog');
  const download = page.waitForEvent('download');
  await dialog.getByRole('link', { name: 'Скачать шаблон CSV для Excel' }).click();
  expect((await download).suggestedFilename()).toBe('team-import-template.csv');
  const content =
    'email;team_code;first_name;last_name;position;hired_at\nteam-file-a@example.com;BROWSER-TEAM;НовыйА;ИзФайла;Engineer;2026-01-01\nteam-file-b@example.com;BROWSER-TEAM;НовыйБ;ИзФайла;Engineer;2026-01-01';
  await dialog
    .locator('input[type=file]')
    .setInputFiles({ name: 'team.csv', mimeType: 'text/csv', buffer: Buffer.from(content) });
  await dialog.getByRole('button', { name: 'Проверить файл', exact: true }).click();
  await expect(dialog.getByRole('status')).toContainText('Новых карточек: 2');
  expect((await (await request.get('/api/employees?q=ИзФайла')).json()).total).toBe(0);
  await dialog.getByRole('button', { name: 'Подтвердить импорт', exact: true }).click();
  await expect(dialog.getByRole('status')).toContainText('Импорт завершён');
  await dialog.getByRole('button', { name: 'Готово', exact: true }).click();
  expect((await (await request.get(`/api/teams/${teamId}`)).json()).member_count).toBe(5);
  await page.getByRole('button', { name: 'Импорт Excel / CSV', exact: true }).click();
  await dialog.locator('input[type=file]').setInputFiles({
    name: 'invalid.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from('email;team_code\nteam-file-a@example.com;UNKNOWN'),
  });
  await dialog.getByRole('button', { name: 'Проверить файл', exact: true }).click();
  await expect(dialog.getByRole('alert')).toContainText('Строка 2');
  await expect(
    dialog.getByRole('button', { name: 'Подтвердить импорт', exact: true }),
  ).toBeDisabled();
  await page.setViewportSize({ width: 390, height: 844 });
  const bounds = await dialog.boundingBox();
  expect(bounds!.width + bounds!.x).toBeLessThanOrEqual(390);
  await page.screenshot({ path: '../artifacts/teams-import-mobile.png' });
  await dialog.getByRole('button', { name: 'Отмена', exact: true }).click();
});
