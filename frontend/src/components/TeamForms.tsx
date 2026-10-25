import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { Team, ImportPreview, ImportResult } from '../lib/teams';
import { teamsApi } from '../lib/teams';
import { useDepartments, useRefreshData } from '../lib/queries';
import { useDebouncedValue } from '../lib/useDebouncedValue';
import { fullName } from '../lib/format';
import { EmployeePicker } from './EmployeePicker';
import { FormError, Modal, Pagination } from './ui';

export function TeamForm({ onClose }: { onClose: () => void }) {
  const departments = useDepartments();
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [department, setDepartment] = useState('');
  const [manager, setManager] = useState<number | null>(null);
  const [supervisor, setSupervisor] = useState<number | null>(null);
  const refresh = useRefreshData();
  const navigate = useNavigate();
  const save = useMutation({
    mutationFn: () =>
      teamsApi.create({
        name,
        code,
        department_id: Number(department),
        manager_id: manager,
        supervisor_id: supervisor,
      }),
    onSuccess: async (team) => {
      await refresh();
      onClose();
      navigate(`/teams/${team.id}`);
    },
  });
  return (
    <Modal
      title="Новая команда"
      onClose={() => {
        if (!save.isPending) onClose();
      }}
    >
      <form
        className="modal-form team-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!save.isPending) save.mutate();
        }}
      >
        <fieldset disabled={save.isPending} className="organization-fields">
          <label>
            Название команды
            <input
              required
              maxLength={100}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            Код команды
            <input
              required
              maxLength={40}
              pattern="[A-Za-z0-9_-]+"
              placeholder="DEV-01"
              value={code}
              onChange={(event) => setCode(event.target.value.toUpperCase())}
            />
          </label>
          <p className="field-hint">
            Уникальный код используется при импорте сотрудников. Латинские буквы, цифры, дефис и
            подчёркивание.
          </p>
          <label>
            Отдел
            <select
              required
              value={department}
              disabled={departments.isPending}
              onChange={(event) => {
                setDepartment(event.target.value);
                setManager(null);
                setSupervisor(null);
              }}
            >
              <option value="">Выберите отдел</option>
              {departments.data?.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          {department && (
            <>
              <EmployeePicker
                label="Руководитель команды"
                value={manager}
                onChange={setManager}
                departmentId={Number(department)}
                emptyLabel="Назначить позже"
              />
              <EmployeePicker
                label="Вышестоящий руководитель"
                value={supervisor}
                onChange={setSupervisor}
                departmentId={Number(department)}
                excludeId={manager ?? undefined}
                emptyLabel={manager ? 'Сохранить текущего, если есть' : 'Не назначен'}
              />
            </>
          )}
          <p className="field-hint">
            Текущие прямые подчинённые руководителя автоматически войдут в команду. Если вышестоящий
            начальник не выбран, сохраняется текущий. Если руководитель ещё не назначен, сотрудники
            временно подчиняются вышестоящему руководителю.
          </p>
        </fieldset>
        <FormError error={save.error ?? departments.error} />
        <div className="modal-actions">
          <button
            type="button"
            className="button secondary"
            disabled={save.isPending}
            onClick={onClose}
          >
            Отмена
          </button>
          <button className="button primary" disabled={save.isPending || !department}>
            {save.isPending ? 'Создаём…' : 'Создать команду'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function ReplaceTeamManager({ team, onClose }: { team: Team; onClose: () => void }) {
  const [manager, setManager] = useState<number | null>(null);
  const refresh = useRefreshData();
  const save = useMutation({
    mutationFn: () => teamsApi.replace(team, manager!),
    onSuccess: async () => {
      await refresh();
      onClose();
    },
  });
  return (
    <Modal
      title="Заменить руководителя команды"
      subtitle={team.name}
      onClose={() => {
        if (!save.isPending) onClose();
      }}
    >
      <form
        className="modal-form team-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!save.isPending && manager) save.mutate();
        }}
      >
        <p>
          Участники команды ({team.member_count}) и подчинённые руководители автоматически перейдут
          к новому руководителю. Вышестоящий начальник сохранится. Прежний руководитель будет
          освобождён от команды; его личная карточка и задачи сохранятся.
        </p>
        <fieldset className="organization-fields" disabled={save.isPending}>
          <EmployeePicker
            label="Новый руководитель"
            required
            value={manager}
            onChange={setManager}
            departmentId={team.department.id}
            excludeId={team.manager?.id}
          />
        </fieldset>
        <FormError error={save.error} />
        <div className="modal-actions">
          <button
            type="button"
            className="button secondary"
            disabled={save.isPending}
            onClick={onClose}
          >
            Отмена
          </button>
          <button className="button primary" disabled={save.isPending || !manager}>
            {save.isPending ? 'Заменяем…' : 'Заменить и передать команду'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function AssignTeamMembers({ team, onClose }: { team: Team; onClose: () => void }) {
  const [search, setSearch] = useState('');
  const q = useDebouncedValue(search);
  const [unassigned, setUnassigned] = useState(true);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const refresh = useRefreshData();
  const people = useQuery({
    queryKey: ['team-candidates', team.id, q, unassigned, page],
    queryFn: () => teamsApi.candidates(team.id, q, unassigned, page),
  });
  const selectAll = useMutation({
    mutationFn: async () => {
      const first = await teamsApi.candidates(team.id, q, unassigned);
      const ids = first.items.map((person) => person.id);
      for (let next = 2; next <= Math.ceil(first.total / 100); next++)
        ids.push(
          ...(await teamsApi.candidates(team.id, q, unassigned, next)).items.map(
            (person) => person.id,
          ),
        );
      return ids;
    },
    onSuccess: (ids) => setSelected((previous) => new Set([...previous, ...ids])),
  });
  const save = useMutation({
    mutationFn: () => teamsApi.assign(team, [...selected]),
    onSuccess: async () => {
      await refresh();
      onClose();
    },
  });
  const busy = save.isPending || selectAll.isPending;
  return (
    <Modal
      title="Назначить сотрудников в команду"
      subtitle={`${team.name} · ${team.department.name}`}
      wide
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <form
        className="modal-form team-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!busy && selected.size) save.mutate();
        }}
      >
        <fieldset className="organization-fields" disabled={busy}>
          <label>
            Поиск сотрудников
            <input
              type="search"
              value={search}
              maxLength={100}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Имя, email или должность"
            />
          </label>
          <label className="organization-checkbox">
            <input
              type="checkbox"
              checked={unassigned}
              onChange={(event) => {
                setUnassigned(event.target.checked);
                setPage(1);
              }}
            />
            Только сотрудники без команды
          </label>
          <p className="field-hint">
            Назначение переведёт выбранных сотрудников из прежних команд. Доступны только сотрудники
            этого отдела.
          </p>
          <div className="team-selection-actions">
            <button
              type="button"
              className="button secondary compact"
              disabled={
                people.isPending || people.isFetching || q !== search || !people.data?.total || busy
              }
              onClick={() => selectAll.mutate()}
            >
              {selectAll.isPending
                ? 'Выбираем…'
                : `Выбрать всех найденных (${people.data?.total ?? 0})`}
            </button>
            <button
              type="button"
              className="button secondary compact"
              onClick={() => setSelected(new Set())}
            >
              Снять выбор
            </button>
            <strong>Выбрано: {selected.size}</strong>
          </div>
          <div className="team-candidate-list">
            {people.isPending ? (
              <p>Загружаем…</p>
            ) : !people.data?.items.length ? (
              <p className="muted">Сотрудники не найдены.</p>
            ) : (
              people.data.items.map((person) => (
                <label key={person.id} className="organization-checkbox">
                  <input
                    type="checkbox"
                    checked={selected.has(person.id)}
                    onChange={() =>
                      setSelected((previous) => {
                        const next = new Set(previous);
                        if (next.has(person.id)) next.delete(person.id);
                        else next.add(person.id);
                        return next;
                      })
                    }
                  />
                  <span>
                    {fullName(person)}
                    <small>
                      {person.position} · {person.email}
                    </small>
                  </span>
                </label>
              ))
            )}
          </div>
          {people.data && (
            <Pagination page={page} total={people.data.total} pageSize={100} onChange={setPage} />
          )}
        </fieldset>
        <FormError error={save.error ?? selectAll.error ?? people.error} />
        <div className="modal-actions">
          <button type="button" className="button secondary" disabled={busy} onClick={onClose}>
            Отмена
          </button>
          <button className="button primary" disabled={busy || !selected.size}>
            {save.isPending ? 'Назначаем…' : `Назначить выбранных (${selected.size})`}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function TeamImportDialog({ onClose }: { onClose: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [fileError, setFileError] = useState<Error | null>(null);
  const refresh = useRefreshData();
  const check = useMutation({
    mutationFn: () => teamsApi.preview(file!),
    onSuccess: setPreview,
    onError: () => setPreview(null),
  });
  const save = useMutation({
    mutationFn: () => teamsApi.import(file!, preview!.fingerprint),
    onSuccess: async (data) => {
      setResult(data);
      await refresh();
    },
  });
  const busy = check.isPending || save.isPending;
  return (
    <Modal
      title="Импорт сотрудников в команды"
      wide
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <div className="modal-form team-form">
        {result ? (
          <>
            <p role="status">
              Импорт завершён. Создано карточек: {result.create_count}. Назначено существующих
              сотрудников: {result.assign_count}. Уже в нужной команде: {result.unchanged_count}.
            </p>
            <button className="button primary" onClick={onClose}>
              Готово
            </button>
          </>
        ) : (
          <>
            <div className="team-import-help">
              <p>
                Сначала создайте команды и укажите их коды в файле. Для существующих сотрудников
                достаточно <strong>email</strong> и <strong>team_code</strong>. Их личные данные
                сохранятся.
              </p>
              <p>
                Для новых карточек заполните также <strong>first_name</strong> (имя),{' '}
                <strong>last_name</strong> (фамилия), <strong>position</strong> (должность),{' '}
                <strong>hired_at</strong> (дата приёма ГГГГ-ММ-ДД). Столбец{' '}
                <strong>department</strong> необязателен: отдел берётся из команды. Аккаунты для
                входа настраиваются отдельно.
              </p>
              <a className="button secondary compact" href="/api/teams/import/template" download>
                Скачать шаблон CSV для Excel
              </a>
            </div>
            <label>
              Файл CSV или Excel (.xlsx), до 5 МБ
              <input
                type="file"
                accept=".csv,.xlsx"
                disabled={busy}
                onChange={(event) => {
                  const next = event.target.files?.[0] ?? null;
                  setFile(next);
                  setPreview(null);
                  setFileError(
                    next && next.size > 5 * 1024 * 1024
                      ? new Error('Размер файла не должен превышать 5 МБ')
                      : null,
                  );
                  check.reset();
                  save.reset();
                }}
              />
            </label>
            <button
              type="button"
              className="button secondary"
              disabled={!file || !!fileError || busy}
              onClick={() => check.mutate()}
            >
              {check.isPending ? 'Проверяем…' : 'Проверить файл'}
            </button>
            <FormError error={fileError ?? check.error ?? save.error} />
            {preview && (
              <>
                <p role="status">
                  Строк: {preview.total}. Новых карточек: {preview.create_count}. Назначений:{' '}
                  {preview.assign_count}. Без изменений: {preview.unchanged_count}. Ошибок:{' '}
                  {preview.error_count}.
                </p>
                {!!preview.error_count && (
                  <div className="team-import-errors" role="alert">
                    <strong>Исправьте ошибки перед импортом</strong>
                    <ul>
                      {preview.errors.map((error, index) => (
                        <li key={index}>
                          Строка {error.line}: {error.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="table-scroll team-import-preview">
                  <table>
                    <thead>
                      <tr>
                        <th>Строка</th>
                        <th>Сотрудник</th>
                        <th>Email</th>
                        <th>Команда</th>
                        <th>Действие</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.map((row) => (
                        <tr key={row.line}>
                          <td>{row.line}</td>
                          <td>{row.name}</td>
                          <td>{row.email}</td>
                          <td>{row.team_code}</td>
                          <td>
                            {
                              {
                                create: 'Создать карточку',
                                assign: 'Назначить в команду',
                                unchanged: 'Без изменений',
                              }[row.action]
                            }
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {preview.total > 100 && (
                  <p className="field-hint">
                    В просмотре показаны первые 100 корректных строк; будут обработаны все{' '}
                    {preview.total} строк.
                  </p>
                )}
              </>
            )}
            <div className="modal-actions">
              <button className="button secondary" disabled={busy} onClick={onClose}>
                Отмена
              </button>
              <button
                className="button primary"
                disabled={!preview || !!preview.error_count || busy || !!fileError}
                onClick={() => save.mutate()}
              >
                {save.isPending ? 'Импортируем…' : 'Подтвердить импорт'}
              </button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
