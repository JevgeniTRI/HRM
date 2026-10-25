import { expect, test } from './fixtures';

test('preview and import a CSV file, then view its journal entry', async ({ page, request }) => {
  await page.goto('/imports');
  await expect(
    page.getByRole('heading', { name: 'Импорт и интеграции', exact: true }),
  ).toBeVisible();
  await page.getByLabel('Источник данных', { exact: true }).fill('browser-csv');
  await page.getByLabel('Файл Excel или CSV').setInputFiles({
    name: 'organization.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(
      'entity;external_id;name;first_name;last_name;email;position;hired_at;department_external_id\ndepartments;D;Импорт из CSV;;;;;;\nemployees;P;;Анна;Импорт;csv-browser@example.com;Инженер;2026-01-01;D\n',
    ),
  });
  await page.getByRole('button', { name: 'Проверить файл', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Результат проверки · 2 записей' })).toBeVisible();
  const before = await (await request.get('/api/employees?q=csv-browser@example.com')).json();
  expect(before.total).toBe(0);
  await page.getByRole('button', { name: 'Импортировать данные', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Импорт завершён · 2 записей');
  await page.getByRole('tab', { name: 'Журнал', exact: true }).click();
  await expect(
    page.locator('.import-history summary').filter({ hasText: 'browser-csv' }),
  ).toBeVisible();
  const people = await (await request.get('/api/employees?q=csv-browser@example.com')).json();
  expect(people.total).toBe(1);
  const person = people.items[0];
  expect((await request.delete(`/api/employees/${person.id}`)).status()).toBe(204);
  expect((await request.delete(`/api/departments/${person.department_id}`)).status()).toBe(204);
});

test('create an API key, import a batch without a cookie and revoke access', async ({
  page,
  request,
  playwright,
}) => {
  await page.goto('/imports');
  await page.getByRole('tab', { name: 'API и ключи' }).click();
  await page.getByLabel('Название интеграции').fill('Браузер SAP');
  await page.getByLabel('Источник API', { exact: true }).fill('browser-sap');
  await page.getByRole('button', { name: 'Создать ключ', exact: true }).click();
  const tokenInput = page.getByLabel('Новый ключ API', { exact: true });
  await expect(tokenInput).toBeVisible();
  const token = await tokenInput.inputValue();
  expect(token.startsWith('hrm_')).toBeTruthy();
  const external = await playwright.request.newContext({
    baseURL: 'http://127.0.0.1:8001',
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  });
  const batch = {
    request_id: 'browser-sap-001',
    departments: [{ external_id: 'D', name: 'API браузер' }],
    skills: [{ external_id: 'S', name: 'Навык API браузер', category: 'Импорт' }],
  };
  const preview = await external.post('/api/integrations/validate', { data: batch });
  expect(preview.status()).toBe(200);
  expect((await preview.json()).errors).toEqual([]);
  const response = await external.post('/api/integrations/imports', { data: batch });
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.total).toBe(2);
  expect(
    (await (await external.post('/api/integrations/imports', { data: batch })).json()).replayed,
  ).toBeTruthy();
  expect((await external.get('/api/accounts')).status()).toBe(401);
  await page.getByRole('button', { name: 'Отозвать ключ «Браузер SAP»', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Отозвать ключ «Браузер SAP»', exact: true }),
  ).toHaveCount(0);
  expect((await external.post('/api/integrations/imports', { data: batch })).status()).toBe(401);
  await external.dispose();
  for (const row of result.records)
    expect((await request.delete(`/api/${row.entity}/${row.id}`)).status()).toBe(204);
});
