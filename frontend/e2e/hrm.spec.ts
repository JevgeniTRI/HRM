import { expect, test } from './fixtures';

test('dashboard and navigation show persisted API data', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Главная', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Пульс навыков' })).toBeVisible();
  await expect(page.locator('.metric-value').first()).toHaveText('12');
  await page.screenshot({ path: '../artifacts/dashboard-desktop.png', fullPage: true });
  await page.getByRole('navigation').getByRole('link', { name: 'Сотрудники' }).click();
  await page.getByRole('textbox', { name: 'Поиск сотрудников' }).fill('МОРОЗОВА');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await page.getByRole('link', { name: 'Анна Морозова anna.morozova@example.com' }).click();
  await expect(
    page.getByRole('heading', { name: 'Анна Морозова', exact: true }).first(),
  ).toBeVisible();
  await expect(page.locator('tbody')).toContainText('React');
  expect(errors).toEqual([]);
});

test('create, assess, reload, update and delete an employee', async ({ page }) => {
  await page.goto('/employees');
  await page.getByRole('button', { name: 'Добавить сотрудника', exact: true }).first().click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Имя', { exact: true }).fill('Тест');
  await dialog.getByLabel('Фамилия').fill('Интерфейса');
  await dialog.getByLabel('Рабочий email').fill('e2e.person@example.com');
  await dialog.getByLabel('Должность').fill('Инженер');
  await dialog
    .getByRole('combobox', { name: 'Подразделение', exact: true })
    .selectOption({ label: 'Разработка' });
  await dialog.getByRole('button', { name: 'Добавить сотрудника' }).click();
  await expect(page).toHaveURL(/\/employees\/\d+$/);
  await page.getByRole('button', { name: 'Добавить навык' }).click();
  await dialog
    .getByRole('combobox', { name: 'Навык', exact: true })
    .selectOption({ label: 'Python' });
  await dialog.getByLabel('Текущий уровень').selectOption('2');
  await dialog.getByLabel('Целевой уровень').selectOption('4');
  await dialog.getByRole('button', { name: 'Сохранить оценку' }).click();
  await expect(page.locator('tbody')).toContainText('Зона развития');
  await page.reload();
  await expect(page.locator('tbody')).toContainText('2 — Базовый');
  await page.getByRole('button', { name: 'Оценить Python' }).click();
  await dialog.getByLabel('Текущий уровень').selectOption('4');
  await dialog.getByRole('button', { name: 'Сохранить оценку' }).click();
  await expect(page.locator('tbody')).toContainText('Цель достигнута');
  await page.getByRole('button', { name: 'Редактировать', exact: true }).click();
  await dialog.getByRole('combobox', { name: 'Статус', exact: true }).selectOption('leave');
  await dialog.getByRole('button', { name: 'Сохранить', exact: true }).click();
  await expect(page.locator('.profile-card')).toContainText('В отпуске');
  await page.getByRole('button', { name: 'Удалить сотрудника', exact: true }).click();
  await dialog.getByRole('button', { name: 'Удалить', exact: true }).click();
  await expect(page).toHaveURL('/employees');
  await page.getByRole('textbox', { name: 'Поиск сотрудников' }).fill('e2e.person@example.com');
  await expect(page.getByRole('heading', { name: 'Сотрудники не найдены' })).toBeVisible();
});

test('matrix editing and referenced skill deletion protection', async ({ page }) => {
  await page.goto('/matrix');
  await page.getByRole('textbox', { name: 'Поиск сотрудников' }).fill('Морозова');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await page
    .getByRole('button', { name: 'Анна Морозова, React: уровень 4, цель 4', exact: true })
    .click();
  await page.getByRole('dialog').getByLabel('Текущий уровень').selectOption('5');
  await page.getByRole('button', { name: 'Сохранить оценку' }).click();
  await expect(
    page.getByRole('button', { name: 'Анна Морозова, React: уровень 5, цель 4', exact: true }),
  ).toBeVisible();
  await page.goto('/skills');
  await page.getByRole('button', { name: 'Удалить React', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Удалить', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Сначала удалите этот навык');
  await page.getByRole('button', { name: 'Отмена', exact: true }).click();
});

test('mobile layout, navigation and accessible dialog keyboard close', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Главная', exact: true })).toBeVisible();
  await page.screenshot({ path: '../artifacts/dashboard-mobile.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByRole('button', { name: 'Открыть меню' }).click();
  await page.getByRole('navigation').getByRole('link', { name: 'Подразделения' }).click();
  await expect(page.getByRole('heading', { name: 'Подразделения', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Добавить подразделение' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
});
