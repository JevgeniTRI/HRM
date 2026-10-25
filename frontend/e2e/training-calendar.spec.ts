import { expect, test } from './fixtures';

test('create scheduled training, open summary, edit and persist across reload', async ({
  page,
  request,
}) => {
  await page.goto('/');
  await page.getByRole('navigation').getByRole('link', { name: 'Календарь обучений' }).click();
  await expect(
    page.getByRole('heading', { name: 'Календарь обучений', exact: true }),
  ).toBeVisible();
  await page.getByLabel('Дата календаря', { exact: true }).fill('2026-10-24');
  await page.getByRole('button', { name: 'Добавить обучение' }).click();
  const dialog = page.getByRole('dialog');
  await dialog
    .getByRole('textbox', { name: 'Название задачи' })
    .fill('Календарь: практикум Python');
  await dialog
    .getByRole('textbox', { name: 'Описание задачи' })
    .fill('Практическое обучение команды');
  await dialog.getByLabel('Начало обучения', { exact: true }).fill('2026-10-24');
  await dialog.getByLabel('Окончание обучения', { exact: true }).fill('2026-10-28');
  await dialog.getByRole('spinbutton', { name: 'Длительность, часов' }).fill('12.5');
  await dialog.getByRole('button', { name: 'Создать обучение', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  const bar = page.getByRole('button', {
    name: 'Открыть сводку: Календарь: практикум Python',
    exact: true,
  });
  await expect(bar).toBeVisible();
  await expect(bar).toContainText('5 дней');
  await expect(bar).toContainText('12,5 ч');
  await bar.click();
  await expect(
    dialog.getByRole('heading', { name: 'Календарь: практикум Python', exact: true }),
  ).toBeVisible();
  await expect(dialog).toContainText('Практическое обучение команды');
  await expect(dialog.locator('dl')).toContainText('5 дней');
  await dialog.getByRole('button', { name: 'Редактировать обучение', exact: true }).click();
  await dialog.getByLabel('Окончание обучения', { exact: true }).fill('2026-10-29');
  await dialog.getByRole('button', { name: 'Сохранить обучение', exact: true }).click();
  await expect(bar).toContainText('6 дней');
  await page.reload();
  await page.getByLabel('Дата календаря', { exact: true }).fill('2026-10-24');
  await expect(bar).toContainText('6 дней');
  await page.screenshot({ path: '../artifacts/training-calendar-desktop.png', fullPage: true });
  const data = await (
    await request.get('/api/tasks?is_training=true&q=Календарь: практикум Python')
  ).json();
  const task = data.items[0];
  expect(task.start_on).toBe('2026-10-24');
  expect(task.end_on).toBe('2026-10-29');
  await request.delete(`/api/tasks/${task.id}?version=${task.version}`);
});

test('year boundaries clip overlapping trainings; zoom, search and year changes update timeline', async ({
  page,
  request,
}) => {
  const response = await request.post('/api/tasks', {
    data: {
      title: 'Календарь: длинный курс',
      learning_source: 'external',
      learning_format: 'individual',
      participant_count: 1,
      duration_hours: '40',
      start_on: '2025-12-28',
      end_on: '2027-01-02',
      status: 'in_progress',
    },
  });
  expect(response.status()).toBe(201);
  const task = await response.json();
  await page.goto('/training-calendar');
  await page.getByLabel('Дата календаря', { exact: true }).fill('2026-10-24');
  await page.getByRole('textbox', { name: 'Поиск обучений' }).fill('длинный курс');
  const bar = page.getByRole('button', {
    name: 'Открыть сводку: Календарь: длинный курс',
    exact: true,
  });
  await expect(bar).toHaveClass(/gantt-continues-left/);
  await expect(bar).toHaveClass(/gantt-continues-right/);
  await expect(bar).toHaveClass(/gantt-bar-in_progress/);
  const monthWidth = await page.locator('.gantt-chart').evaluate((element) => element.scrollWidth);
  await page.getByRole('combobox', { name: 'Масштаб календаря' }).selectOption('week');
  await expect(page.locator('.gantt-day')).toHaveCount(365);
  await expect
    .poll(() => page.locator('.gantt-chart').evaluate((element) => element.scrollWidth))
    .toBeGreaterThan(monthWidth);
  await expect(bar).toBeVisible();
  await page.getByLabel('Дата календаря', { exact: true }).fill('2028-12-01');
  await expect(bar).not.toBeVisible();
  await expect(page.getByText('В этом году нет запланированных обучений')).toBeVisible();
  await expect(page.locator('.gantt-day')).toHaveCount(366);
  await page.getByLabel('Дата календаря', { exact: true }).fill('2026-10-24');
  await expect(bar).toBeVisible();
  await request.delete(`/api/tasks/${task.id}?version=${task.version}`);
});

test('timeline covers January through December and loads trainings across the whole year', async ({
  page,
  request,
}) => {
  const tasks = [];
  for (const [month, title] of [
    ['01', 'Январский курс'],
    ['12', 'Декабрьский курс'],
  ]) {
    const response = await request.post('/api/tasks', {
      data: {
        title,
        learning_source: 'internal',
        learning_format: 'individual',
        participant_count: 1,
        start_on: `2026-${month}-10`,
        end_on: `2026-${month}-15`,
        duration_hours: '8',
      },
    });
    expect(response.status()).toBe(201);
    tasks.push(await response.json());
  }
  const ranges: string[] = [];
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.pathname === '/api/tasks/calendar')
      ranges.push(`${url.searchParams.get('from_on')}/${url.searchParams.get('to_on')}`);
  });
  await page.goto('/training-calendar');
  await page.getByLabel('Дата календаря', { exact: true }).fill('2026-10-24');
  await expect(page.locator('.gantt-day')).toHaveCount(365);
  await expect(page.locator('.gantt-month')).toHaveCount(12);
  const chart = page.getByRole('region', { name: 'Диаграмма Ганта обучений' });
  await chart.evaluate((element) => {
    element.scrollLeft = 0;
  });
  await expect.poll(() => chart.evaluate((element) => element.scrollLeft)).toBe(0);
  await expect(page.getByLabel('Дата календаря', { exact: true })).toHaveValue('2026-01-01');
  const january = page.getByRole('button', { name: 'Открыть сводку: Январский курс', exact: true });
  await expect(january).toBeInViewport();
  await chart.evaluate((element) => {
    element.scrollLeft = element.scrollWidth;
  });
  const december = page.getByRole('button', {
    name: 'Открыть сводку: Декабрьский курс',
    exact: true,
  });
  await expect(december).toBeInViewport();
  await expect(page.locator('.calendar-period-controls h2')).toContainText(/декабрь/i);
  await december.click();
  await expect(page.getByRole('dialog')).toContainText('Декабрьский курс');
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Закрыть', exact: true })
    .last()
    .click();
  expect(ranges).toContain('2026-01-01/2026-12-31');
  await page.getByLabel('Дата календаря', { exact: true }).fill('2024-02-29');
  await expect(page.locator('.gantt-day')).toHaveCount(366);
  await expect(page.locator('.gantt-day[aria-label^="29 февр"]')).toBeInViewport();
  await expect(chart).toBeVisible();
  for (const task of tasks) await request.delete(`/api/tasks/${task.id}?version=${task.version}`);
});

test('unscheduled training can receive dates and mobile calendar scrolls within the page', async ({
  page,
  request,
}) => {
  const task = await (
    await request.post('/api/tasks', {
      data: {
        title: 'Календарь: назначить даты',
        learning_source: 'internal',
        learning_format: 'individual',
        participant_count: 1,
        duration_hours: '2',
      },
    })
  ).json();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/training-calendar');
  await page.getByLabel('Дата календаря', { exact: true }).fill('2026-10-24');
  await page
    .getByRole('button', { name: 'Назначить даты: Календарь: назначить даты', exact: true })
    .click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Начало обучения', { exact: true }).fill('2026-10-24');
  await dialog.getByLabel('Окончание обучения', { exact: true }).fill('2026-10-24');
  await dialog.getByRole('button', { name: 'Сохранить обучение', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Открыть сводку: Календарь: назначить даты', exact: true }),
  ).toBeAttached();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page
    .getByRole('button', { name: 'Открыть обучение Календарь: назначить даты', exact: true })
    .click();
  await expect(dialog).toContainText('1 день');
  await dialog.getByRole('button', { name: 'Закрыть', exact: true }).last().click();
  await page.screenshot({ path: '../artifacts/training-calendar-mobile.png', fullPage: true });
  const saved = await (await request.get(`/api/tasks/${task.id}`)).json();
  await request.delete(`/api/tasks/${task.id}?version=${saved.version}`);
});
