import { expect, test } from './fixtures';

const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII=',
  'base64',
);

test('certificates can be added under skills, from a profile, and from an assessment', async ({
  page,
  request,
}) => {
  const departments = await (await request.get('http://127.0.0.1:8001/api/departments')).json();
  const skills = await (await request.get('http://127.0.0.1:8001/api/skills')).json();
  const employee = await (
    await request.post('http://127.0.0.1:8001/api/employees', {
      data: {
        first_name: 'Тест',
        last_name: 'Сертификатов',
        email: 'certificates.e2e@example.com',
        position: 'Инженер',
        department_id: departments[0].id,
        status: 'active',
        hired_at: '2026-09-01',
      },
    })
  ).json();
  const python = skills.find((skill: { name: string }) => skill.name === 'Python');
  const react = skills.find((skill: { name: string }) => skill.name === 'React');
  const employeePath = `http://127.0.0.1:8001/api/employees/${employee.id}`;
  for (const skill of [python, react]) {
    const response = await request.put(`${employeePath}/skills/${skill.id}`, {
      data: { current_level: 3, target_level: 4 },
    });
    expect(response.ok()).toBeTruthy();
  }
  try {
    await page.goto(`/employees/${employee.id}`);
    const section = page.getByRole('region', { name: 'Сертификаты сотрудника' });
    const dialog = page.getByRole('dialog');
    await expect(section.getByRole('heading', { name: 'Сертификатов пока нет' })).toBeVisible();
    await page
      .getByRole('button', { name: 'Добавить сертификат к навыку Python', exact: true })
      .click();
    await expect(dialog.getByLabel('Навык для сертификата')).toHaveValue(String(python.id));
    await dialog.getByLabel('Название сертификата').fill('Python Certificate');
    await dialog
      .getByLabel('Файл сертификата')
      .setInputFiles({ name: 'certificate.png', mimeType: 'image/png', buffer: png });
    await dialog.getByRole('button', { name: 'Загрузить сертификат' }).click();
    await expect(dialog).not.toBeVisible();
    await expect(
      section.getByRole('link', { name: 'Просмотреть сертификат Python Certificate' }),
    ).toBeVisible();
    await expect(page.locator('tbody tr').filter({ hasText: 'Python' })).toContainText(
      'Python Certificate',
    );

    await section.getByRole('button', { name: 'Добавить сертификат', exact: true }).click();
    await dialog.getByLabel('Навык для сертификата').selectOption(String(react.id));
    await dialog
      .getByLabel('Файл сертификата')
      .setInputFiles({ name: 'React.png', mimeType: 'image/png', buffer: png });
    await dialog.getByRole('button', { name: 'Загрузить сертификат' }).click();
    await expect(dialog).not.toBeVisible();
    await expect(
      section.getByRole('link', { name: 'Просмотреть сертификат React.png' }),
    ).toBeVisible();

    await page.getByRole('button', { name: 'Оценить Python', exact: true }).click();
    await expect(
      dialog.getByRole('link', { name: 'Просмотреть сертификат Python Certificate' }),
    ).toBeVisible();
    await dialog.getByLabel('Название сертификата').fill('Advanced Python');
    await dialog
      .getByLabel('Файл сертификата')
      .setInputFiles({ name: 'advanced.png', mimeType: 'image/png', buffer: png });
    await dialog.getByRole('button', { name: 'Загрузить сертификат' }).click();
    await expect(
      dialog.getByRole('link', { name: 'Просмотреть сертификат Advanced Python' }),
    ).toBeVisible();
    await dialog.getByRole('button', { name: 'Сохранить оценку' }).click();
    await expect(dialog).not.toBeVisible();
    await page.reload();
    await expect(section.locator('.certificate-item')).toHaveCount(3);

    const popupPromise = page.waitForEvent('popup');
    await section.getByRole('link', { name: 'Просмотреть сертификат Python Certificate' }).click();
    const popup = await popupPromise;
    await popup.waitForLoadState();
    await expect(popup.locator('img')).toBeVisible();
    expect(await popup.locator('img').evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(
      1,
    );
    await popup.close();
    const downloadPromise = page.waitForEvent('download');
    await section.getByRole('link', { name: 'Скачать сертификат Python Certificate' }).click();
    expect((await downloadPromise).suggestedFilename()).toBe('certificate.png');
    await page.screenshot({ path: '../artifacts/certificates-desktop.png', fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload();
    await expect(section.locator('.certificate-item')).toHaveCount(3);
    await page.screenshot({ path: '../artifacts/certificates-mobile.png', fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      390,
    );

    await section.getByRole('button', { name: 'Удалить сертификат Advanced Python' }).click();
    await section.getByRole('button', { name: 'Подтвердить удаление' }).click();
    await expect(section.locator('.certificate-item')).toHaveCount(2);
    await page.reload();
    await expect(
      section.getByRole('link', { name: 'Просмотреть сертификат Advanced Python' }),
    ).toHaveCount(0);
  } finally {
    await request.delete(employeePath);
  }
});

test('upload validation keeps the dialog open and allows retry', async ({ page }) => {
  await page.goto('/employees');
  await page.getByRole('textbox', { name: 'Поиск сотрудников' }).fill('anna.morozova@example.com');
  await page.getByRole('link', { name: 'Анна Морозова anna.morozova@example.com' }).click();
  await page
    .getByRole('button', { name: 'Добавить сертификат к навыку React', exact: true })
    .click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Файл сертификата').setInputFiles({
    name: 'fake.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('invalid pdf'),
  });
  await dialog.getByRole('button', { name: 'Загрузить сертификат' }).click();
  await expect(dialog.getByRole('alert')).toContainText('Содержимое файла не соответствует');
  await expect(dialog).toBeVisible();
  await dialog.getByLabel('Файл сертификата').setInputFiles({
    name: 'huge.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.alloc(15 * 1024 * 1024 + 1),
  });
  await dialog.getByRole('button', { name: 'Загрузить сертификат' }).click();
  await expect(dialog.getByRole('alert')).toContainText('до 15 МБ');
  await dialog.getByRole('button', { name: 'Закрыть', exact: true }).click();
  await expect(dialog).not.toBeVisible();
});
