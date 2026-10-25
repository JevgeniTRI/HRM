import { expect, test } from './fixtures';

test('board shows three columns, department tags and training effort', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('navigation').getByRole('link', { name: 'Задачи и обучение' }).click();
  await expect(page.getByRole('heading', { name: 'Kanban-доска' })).toBeVisible();
  for (const name of ['To Do', 'In Progress', 'Done']) {
    await expect(page.getByRole('region', { name, exact: true })).toBeVisible();
  }
  const training = page.getByRole('article', {
    name: 'Задача: Командная коммуникация',
    exact: true,
  });
  await expect(training).toContainText('15');
  await expect(training).toContainText('10 участников');
  await expect(training).toContainText('Дизайн');
  await expect(page.locator('.task-metrics .metric-value').first()).toHaveText('6');
  await page.screenshot({ path: '../artifacts/kanban-desktop.png', fullPage: true });
});

test('create training, preview 15 hours, move, reload, edit and delete', async ({ page }) => {
  await page.goto('/tasks');
  await page.getByRole('button', { name: 'Создать задачу', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('textbox', { name: 'Название задачи' }).fill('Практикум E2E');
  await dialog
    .getByRole('combobox', { name: 'Источник обучения в карточке' })
    .selectOption('external');
  await dialog.getByRole('combobox', { name: 'Формат обучения в карточке' }).selectOption('group');
  await dialog.getByRole('spinbutton', { name: 'Длительность, часов' }).fill('1.5');
  await dialog.getByRole('spinbutton', { name: 'Число участников' }).fill('10');
  await dialog.getByRole('checkbox', { name: 'Разработка', exact: true }).check();
  await dialog.getByRole('checkbox', { name: 'Дизайн', exact: true }).check();
  await dialog.getByRole('spinbutton', { name: 'Стоимость всего' }).fill('49.90');
  await expect(dialog.getByText('15 человекочасов', { exact: true })).toBeVisible();
  await dialog.getByRole('button', { name: 'Создать задачу', exact: true }).click();
  const card = page.getByRole('article', { name: 'Задача: Практикум E2E', exact: true });
  await expect(card).toContainText('49,90');
  await card
    .getByRole('combobox', { name: 'Статус задачи Практикум E2E' })
    .selectOption('in_progress');
  await expect(
    page
      .getByRole('region', { name: 'In Progress', exact: true })
      .getByRole('article', { name: 'Задача: Практикум E2E', exact: true }),
  ).toBeVisible();
  await expect(card).not.toHaveClass(/task-saving/);
  await page.reload();
  await expect(
    page
      .getByRole('region', { name: 'In Progress', exact: true })
      .getByRole('article', { name: 'Задача: Практикум E2E', exact: true }),
  ).toBeVisible();
  await card.getByRole('button', { name: 'Редактировать задачу Практикум E2E' }).click();
  await dialog.getByRole('spinbutton', { name: 'Длительность, часов' }).fill('2');
  await expect(dialog.getByText('20 человекочасов', { exact: true })).toBeVisible();
  await dialog.getByRole('button', { name: 'Сохранить задачу', exact: true }).click();
  await expect(card.locator('.task-totals')).toContainText('20');
  await card.getByRole('button', { name: 'Удалить задачу Практикум E2E' }).click();
  await dialog.getByRole('button', { name: 'Удалить', exact: true }).click();
  await expect(card).not.toBeVisible();
});

test('native drag and drop persists status', async ({ page, request }) => {
  const response = await request.post('/api/tasks', { data: { title: 'Перетащить E2E' } });
  const task = await response.json();
  expect(response.status()).toBe(201);
  await page.goto('/tasks');
  const card = page.getByRole('article', { name: 'Задача: Перетащить E2E', exact: true });
  await card.dragTo(
    page.getByRole('region', { name: 'Done', exact: true }).locator('.kanban-column-heading'),
    { sourcePosition: { x: 22, y: 22 }, targetPosition: { x: 30, y: 22 } },
  );
  const moved = page
    .getByRole('region', { name: 'Done', exact: true })
    .getByRole('article', { name: 'Задача: Перетащить E2E', exact: true });
  await expect(moved).toBeVisible();
  await expect(moved).not.toHaveClass(/task-saving/);
  const persisted = await (await request.get(`/api/tasks/${task.id}`)).json();
  expect(persisted.status).toBe('done');
  await request.delete(`/api/tasks/${task.id}?version=${persisted.version}`);
});

test('filters work together, persist in URL and update summary', async ({ page, request }) => {
  const departments = await (await request.get('/api/departments')).json();
  const design = departments.find((department: { name: string }) => department.name === 'Дизайн');
  await page.goto('/tasks');
  await page
    .getByRole('combobox', { name: 'Источник обучения', exact: true })
    .selectOption('internal');
  await expect(page).toHaveURL(/learning_source=internal/);
  await page.getByRole('combobox', { name: 'Формат обучения', exact: true }).selectOption('group');
  await expect(page).toHaveURL(/learning_format=group/);
  await page
    .getByRole('combobox', { name: 'Подразделение задачи' })
    .selectOption(String(design.id));
  await expect(page).toHaveURL(new RegExp(`department_id=${design.id}(?:&|$)`));
  await expect(page.getByRole('article')).toHaveCount(1);
  await expect(page.locator('.task-metrics .metric-value').first()).toHaveText('1');
  await expect(page.locator('.task-metrics .metric-value').nth(2)).toContainText('15');
  await page.reload();
  await expect(
    page.getByRole('article', { name: 'Задача: Командная коммуникация', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Сбросить', exact: true }).click();
  await page.getByRole('textbox', { name: 'Поиск задач' }).fill('КОММУНИКАЦИЯ');
  await expect(page.getByRole('article')).toHaveCount(1);
  await page.getByRole('textbox', { name: 'Поиск задач' }).fill('Не существует такой задачи');
  await expect(page.getByRole('article')).toHaveCount(0);
  await expect(page.locator('.task-metrics .metric-value').first()).toHaveText('0');
});

test('failed move rolls card back to its original column', async ({ page, request }) => {
  const task = await (
    await request.post('/api/tasks', { data: { title: 'Откат статуса E2E' } })
  ).json();
  await page.route(`**/api/tasks/${task.id}/status`, (route) =>
    route.fulfill({ status: 503, json: { detail: 'Сохранение временно недоступно' } }),
  );
  await page.goto('/tasks');
  const card = page.getByRole('article', { name: 'Задача: Откат статуса E2E', exact: true });
  await card
    .getByRole('combobox', { name: 'Статус задачи Откат статуса E2E' })
    .selectOption('done');
  await expect(page.getByRole('alert')).toContainText('Сохранение временно недоступно');
  await expect(
    page
      .getByRole('region', { name: 'To Do', exact: true })
      .getByRole('article', { name: 'Задача: Откат статуса E2E', exact: true }),
  ).toBeVisible();
  await expect(card).not.toHaveClass(/task-saving/);
  await request.delete(`/api/tasks/${task.id}?version=1`);
});

test('stale edit is rejected without overwriting another status change', async ({
  page,
  request,
}) => {
  const task = await (
    await request.post('/api/tasks', { data: { title: 'Конкурентное изменение E2E' } })
  ).json();
  await page.goto('/tasks');
  await page
    .getByRole('button', { name: 'Редактировать задачу Конкурентное изменение E2E' })
    .click();
  const dialog = page.getByRole('dialog');
  await request.put(`/api/tasks/${task.id}/status`, {
    data: { status: 'in_progress', version: 1 },
  });
  await dialog.getByRole('textbox', { name: 'Название задачи' }).fill('Не должно сохраниться');
  await dialog.getByRole('button', { name: 'Сохранить задачу' }).click();
  await expect(dialog.getByRole('alert')).toContainText('Задача уже изменена');
  const persisted = await (await request.get(`/api/tasks/${task.id}`)).json();
  expect(persisted.title).toBe('Конкурентное изменение E2E');
  expect(persisted.status).toBe('in_progress');
  await request.delete(`/api/tasks/${task.id}?version=${persisted.version}`);
});

test('mobile board fits screen and allows ordinary tasks without training fields', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/tasks');
  await expect(
    page.getByRole('article', { name: 'Задача: Командная коммуникация', exact: true }),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: '../artifacts/kanban-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Создать задачу', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('textbox', { name: 'Название задачи' }).fill('Обычная задача E2E');
  await dialog.getByRole('checkbox', { name: /Это обучение/ }).uncheck();
  await expect(dialog.getByRole('spinbutton', { name: 'Длительность, часов' })).not.toBeVisible();
  await dialog.getByRole('button', { name: 'Создать задачу', exact: true }).click();
  const card = page.getByRole('article', { name: 'Задача: Обычная задача E2E', exact: true });
  await expect(card).toContainText('Обычная задача');
  await card.getByRole('button', { name: 'Удалить задачу Обычная задача E2E' }).click();
  await dialog.getByRole('button', { name: 'Удалить', exact: true }).click();
  await expect(card).not.toBeVisible();
});
