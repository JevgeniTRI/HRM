import { expect, test } from './fixtures';

test('numeric descriptions persist and level 10 works in the profile and matrix', async ({
  page,
  request,
}) => {
  await page.goto('/skills');
  await page.getByRole('button', { name: 'Добавить навык', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('textbox', { name: 'Название', exact: true }).fill('Excel E2E шкала');
  await dialog.getByRole('combobox', { name: 'Категория', exact: true }).fill('Технические');
  await dialog
    .getByRole('textbox', { name: 'Описание навыка', exact: true })
    .fill('Существующее описание сохраняется отдельно');
  await expect(dialog.getByRole('combobox', { name: 'Конец диапазона' })).toHaveValue('10');
  await expect(dialog.locator('.skill-level-editor')).toHaveCount(11);
  await dialog
    .getByRole('textbox', { name: 'Название уровня 10', exact: true })
    .fill('Эксперт Excel');
  await dialog
    .getByRole('textbox', { name: 'Описание уровня 0', exact: true })
    .fill('Не открывал Excel');
  await dialog
    .getByRole('textbox', { name: 'Описание уровня 10', exact: true })
    .fill('Автоматизирует отчётность');
  await page.screenshot({ path: '../artifacts/skill-scale-numeric.png', fullPage: true });
  await dialog.getByRole('button', { name: 'Сохранить', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Excel E2E шкала', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Редактировать Excel E2E шкала', exact: true }).click();
  await expect(
    dialog.getByRole('textbox', { name: 'Описание уровня 10', exact: true }),
  ).toHaveValue('Автоматизирует отчётность');
  await expect(dialog.getByRole('textbox', { name: 'Описание навыка', exact: true })).toHaveValue(
    'Существующее описание сохраняется отдельно',
  );
  await dialog.getByRole('button', { name: 'Отмена', exact: true }).click();
  const employee = (await (await request.get('/api/employees?page_size=1')).json()).items[0];
  const skill = (await (await request.get('/api/skills')).json()).find(
    (item: { name: string }) => item.name === 'Excel E2E шкала',
  );
  await page.goto(`/employees/${employee.id}`);
  await page.getByRole('button', { name: 'Добавить навык', exact: true }).click();
  await dialog.getByRole('combobox', { name: 'Навык', exact: true }).selectOption(String(skill.id));
  await dialog.getByRole('combobox', { name: 'Текущий уровень' }).selectOption('10');
  await dialog.getByRole('combobox', { name: 'Целевой уровень' }).selectOption('10');
  await dialog.getByRole('button', { name: 'Сохранить оценку', exact: true }).click();
  await expect(page.locator('tbody')).toContainText('10 — Эксперт Excel');
  await page
    .getByRole('button', {
      name: 'Текущий уровень Excel E2E шкала: 10 — Эксперт Excel',
      exact: true,
    })
    .click();
  await expect(dialog.locator('.skill-level-reference > li')).toHaveCount(11);
  await expect(dialog).toContainText('Автоматизирует отчётность');
  await dialog.getByRole('button', { name: 'Закрыть', exact: true }).last().click();
  await page.goto(`/matrix?q=${encodeURIComponent(employee.email)}`);
  const cell = page.getByRole('button', {
    name: `${employee.first_name} ${employee.last_name}, Excel E2E шкала: уровень 10, цель 10`,
    exact: true,
  });
  await expect(cell).toHaveClass(/met/);
  await expect(cell).toHaveAttribute('title', /Автоматизирует отчётность/);
  await request.delete(`/api/employees/${employee.id}/skills/${skill.id}`);
  await request.delete(`/api/skills/${skill.id}`);
});

test('letter range C–Z supports descriptions, matrix editing and narrowing protection on mobile', async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/skills');
  await page.getByRole('button', { name: 'Добавить навык', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('textbox', { name: 'Название', exact: true }).fill('Буквенная шкала E2E');
  await dialog.getByRole('combobox', { name: 'Категория', exact: true }).fill('Языки');
  await dialog.getByRole('combobox', { name: 'Тип шкалы' }).selectOption('letter');
  await dialog.getByRole('combobox', { name: 'Начало диапазона' }).selectOption('2');
  await dialog.getByRole('textbox', { name: 'Название уровня C', exact: true }).fill('Базовый');
  await dialog.getByRole('textbox', { name: 'Название уровня Z', exact: true }).fill('Эксперт');
  await dialog
    .getByRole('textbox', { name: 'Описание уровня C', exact: true })
    .fill('Работает с подсказкой');
  await dialog
    .getByRole('textbox', { name: 'Описание уровня Z', exact: true })
    .fill('Обучает других');
  await expect(dialog.locator('.skill-level-editor')).toHaveCount(24);
  await page.screenshot({ path: '../artifacts/skill-scale-letter-mobile.png', fullPage: true });
  await dialog.getByRole('button', { name: 'Сохранить', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  const employee = (await (await request.get('/api/employees?page_size=1')).json()).items[0];
  const skill = (await (await request.get('/api/skills')).json()).find(
    (item: { name: string }) => item.name === 'Буквенная шкала E2E',
  );
  await page.goto(`/employees/${employee.id}`);
  await page.getByRole('button', { name: 'Добавить навык', exact: true }).click();
  await dialog.getByRole('combobox', { name: 'Навык', exact: true }).selectOption(String(skill.id));
  await expect(
    dialog
      .getByRole('combobox', { name: 'Текущий уровень' })
      .getByRole('option', { name: 'C — Базовый', exact: true }),
  ).toBeAttached();
  await dialog.getByRole('combobox', { name: 'Текущий уровень' }).selectOption('2');
  await dialog.getByRole('combobox', { name: 'Целевой уровень' }).selectOption('25');
  await dialog.getByRole('button', { name: 'Сохранить оценку', exact: true }).click();
  await expect(page.locator('tbody')).toContainText('C — Базовый');
  await expect(page.locator('tbody')).toContainText('Z — Эксперт');
  await page
    .getByRole('button', { name: 'Текущий уровень Буквенная шкала E2E: C — Базовый', exact: true })
    .click();
  await expect(dialog.locator('.skill-level-reference > li')).toHaveCount(24);
  await expect(dialog).toContainText('Работает с подсказкой');
  await expect(dialog).toContainText('Обучает других');
  await dialog.getByRole('button', { name: 'Закрыть', exact: true }).last().click();
  await page.goto(`/matrix?q=${encodeURIComponent(employee.email)}`);
  await page
    .getByRole('button', {
      name: `${employee.first_name} ${employee.last_name}, Буквенная шкала E2E: уровень C, цель Z`,
      exact: true,
    })
    .click();
  await dialog.getByRole('combobox', { name: 'Текущий уровень' }).selectOption('25');
  await dialog.getByRole('button', { name: 'Сохранить оценку', exact: true }).click();
  await expect(
    page.getByRole('button', {
      name: `${employee.first_name} ${employee.last_name}, Буквенная шкала E2E: уровень Z, цель Z`,
      exact: true,
    }),
  ).toHaveClass(/met/);
  await page.goto('/skills');
  await page
    .getByRole('button', { name: 'Редактировать Буквенная шкала E2E', exact: true })
    .click();
  await dialog.getByRole('combobox', { name: 'Конец диапазона' }).selectOption('24');
  await dialog.getByRole('button', { name: 'Сохранить', exact: true }).click();
  await expect(dialog.getByRole('alert')).toContainText('исключает существующие оценки');
  await dialog.getByRole('button', { name: 'Отмена', exact: true }).click();
  await request.delete(`/api/employees/${employee.id}/skills/${skill.id}`);
  await request.delete(`/api/skills/${skill.id}`);
});
