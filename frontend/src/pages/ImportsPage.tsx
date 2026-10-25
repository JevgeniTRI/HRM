import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Download, FileUp, KeyRound, Plug, History, Copy } from 'lucide-react';
import { PageHeader, FormError, Loading, ErrorState, Empty } from '../components/ui';
import { request } from '../lib/api';
import { useAuth } from '../lib/auth';
import { entityLabels, fileImport } from '../lib/imports';
import type { Entity, ImportResult, ImportRun, IntegrationKey } from '../lib/imports';
import './imports.css';

const entities = Object.keys(entityLabels) as Entity[];
const actionLabels: Record<string, string> = {
  created: 'Создание',
  updated: 'Обновление',
  unchanged: 'Без изменений',
};
function Counts({ result }: { result: ImportResult }) {
  return (
    <div className="import-counts">
      {entities.map((entity) => {
        const count = result.counts?.[entity];
        return (
          count && (
            <div key={entity}>
              <strong>{entityLabels[entity]}</strong>
              <span>
                Создать: {count.created} · обновить: {count.updated} · без изменений:{' '}
                {count.unchanged}
              </span>
            </div>
          )
        );
      })}
    </div>
  );
}
function Issues({ result }: { result: ImportResult }) {
  return result.errors?.length ? (
    <div className="import-issues" role="alert">
      <strong>Ошибки: {result.error_count ?? result.errors.length}. Данные не сохранены.</strong>
      <ul>
        {result.errors.map((error, index) => (
          <li key={index}>
            {error.sheet && `${error.sheet}, `}
            {error.line && `строка ${error.line}, `}
            {entityLabels[error.entity as Entity] ?? error.entity} {error.external_id}:{' '}
            {error.message}
          </li>
        ))}
      </ul>
    </div>
  ) : null;
}
function Files() {
  const cache = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState('manual');
  const [plan, setPlan] = useState<ImportResult | null>(null);
  const [done, setDone] = useState<ImportResult | null>(null);
  const [requestId, setRequestId] = useState('');
  const preview = useMutation({
    mutationFn: () => fileImport(file!, source),
    onSuccess: (data) => {
      setPlan(data);
      setDone(null);
      setRequestId(crypto.randomUUID());
    },
  });
  const apply = useMutation({
    mutationFn: () =>
      fileImport(file!, source, { fingerprint: plan!.fingerprint!, request_id: requestId }),
    onSuccess: (data) => {
      setDone(data);
      setPlan(null);
      void cache.invalidateQueries();
    },
  });
  const busy = preview.isPending || apply.isPending;
  function reset() {
    setPlan(null);
    setDone(null);
    preview.reset();
    apply.reset();
  }
  return (
    <section className="card import-panel">
      <h2>Загрузка Excel / CSV</h2>
      <p>
        Создайте отделы, сотрудников, команды и навыки одним файлом. Существующие записи будут
        обновлены по внешнему ID.
      </p>
      <div className="import-actions">
        <a className="button secondary" href="/api/imports/template/xlsx" download>
          <Download size={17} />
          Шаблон Excel
        </a>
        <a className="button secondary" href="/api/imports/template/csv" download>
          <Download size={17} />
          Шаблон CSV
        </a>
      </div>
      <details className="import-help">
        <summary>Как подготовить файл</summary>
        <p>
          В Excel заполните листы departments (отделы), employees (сотрудники), teams (команды),
          skills (навыки). В CSV укажите тип строки в столбце entity.
        </p>
        <p>
          Для каждой записи задайте постоянный external_id. Связи department_external_id,
          team_external_id, manager_external_id и supervisor_external_id ссылаются на ID записей
          того же источника. Можно передать все связи в одном файле.
        </p>
        <p>
          Для нового сотрудника нужны first_name, last_name, email, position, hired_at (ГГГГ-ММ-ДД),
          department_external_id. Для команды — name, code, department_external_id; для отдела —
          name; для навыка — name, category. Руководитель команды задаётся через
          manager_external_id, вышестоящий — через supervisor_external_id. Статус сотрудника:
          active, probation, leave или inactive.
        </p>
        <p>
          Пустые ячейки сохраняют текущее значение. Для очистки необязательного поля используйте
          #NULL. Внешние ID храните как текст, особенно если они начинаются с нуля. Пароли и роли
          доступа задаются в разделе «Аккаунты и доступ».
        </p>
      </details>
      <form
        className="import-file-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (!busy && file) {
            setPlan(null);
            setDone(null);
            apply.reset();
            preview.mutate();
          }
        }}
      >
        <label>
          Источник данных
          <input
            required
            maxLength={40}
            pattern="[a-zA-Z0-9_.-]+"
            value={source}
            disabled={busy}
            onChange={(e) => {
              setSource(e.target.value.toLowerCase());
              reset();
            }}
          />
        </label>
        <label>
          Файл Excel или CSV
          <input
            type="file"
            accept=".xlsx,.csv"
            required
            disabled={busy}
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              reset();
            }}
          />
        </label>
        <button className="button primary" disabled={!file || busy}>
          <FileUp size={17} />
          {preview.isPending ? 'Проверяем…' : 'Проверить файл'}
        </button>
      </form>
      <p className="field-hint">
        До 5 МБ и 10 000 записей. Сохраняйте один источник при повторных загрузках, например manual
        или sap.
      </p>
      <FormError error={preview.error} />
      <FormError error={apply.error} />
      {plan && (
        <div className="import-preview">
          <h3>Результат проверки · {plan.total} записей</h3>
          <Counts result={plan} />
          <Issues result={plan} />
          {!plan.error_count && (
            <>
              <p>
                Изменения затронут также существующих сотрудников: {plan.affected_employees ?? 0}.
                При замене руководителя состав команды сохранится.
              </p>
              <div className="import-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Тип</th>
                      <th>Внешний ID</th>
                      <th>Название / сотрудник</th>
                      <th>Действие</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plan.records.map((row) => (
                      <tr key={`${row.entity}:${row.external_id}`}>
                        <td>{entityLabels[row.entity]}</td>
                        <td>{row.external_id}</td>
                        <td>{row.label}</td>
                        <td>{actionLabels[row.action]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {plan.total > 100 && (
                <p className="field-hint">Показаны первые 100 записей. Импортируется весь файл.</p>
              )}
              <button
                className="button primary"
                disabled={busy || !!apply.error}
                onClick={() => apply.mutate()}
              >
                {apply.isPending ? 'Импортируем…' : 'Импортировать данные'}
              </button>
              <p className="field-hint">
                Пакет сохраняется целиком. При ошибке ни одна запись не будет изменена.
              </p>
            </>
          )}
        </div>
      )}
      {done && (
        <div className="import-success" role="status">
          <CheckCircle2 size={22} />
          <div>
            <strong>Импорт завершён · {done.total} записей</strong>
            <Counts result={done} />
          </div>
        </div>
      )}
    </section>
  );
}

function Keys() {
  const cache = useQueryClient();
  const list = useQuery({
    queryKey: ['integration-keys'],
    queryFn: () => request<IntegrationKey[]>('/imports/keys'),
  });
  const [name, setName] = useState('');
  const [source, setSource] = useState('sap');
  const [scopes, setScopes] = useState<Entity[]>(entities);
  const [expiry, setExpiry] = useState('');
  const [secret, setSecret] = useState('');
  const [copied, setCopied] = useState(false);
  const create = useMutation({
    mutationFn: () =>
      request<{ key: IntegrationKey; token: string }>('/imports/keys', {
        method: 'POST',
        body: JSON.stringify({
          name,
          source,
          entities: scopes,
          expires_at: expiry ? new Date(expiry).toISOString() : null,
        }),
      }),
    onSuccess: (data) => {
      setSecret(data.token);
      setCopied(false);
      setName('');
      void cache.invalidateQueries({ queryKey: ['integration-keys'] });
    },
  });
  const revoke = useMutation({
    mutationFn: (id: number) => request(`/imports/keys/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      setSecret('');
      void cache.invalidateQueries({ queryKey: ['integration-keys'] });
    },
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!create.isPending && scopes.length) create.mutate();
  }
  return (
    <section className="card import-panel">
      <h2>Ключи интеграции</h2>
      <p>
        Ключ разрешает импорт выбранных типов данных только от указанного источника. Передайте его
        настройщику внешней системы.
      </p>
      <form onSubmit={submit} className="import-key-form">
        <div className="import-form-grid">
          <label>
            Название интеграции
            <input
              required
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например, SAP HR"
            />
          </label>
          <label>
            Источник API
            <input
              required
              pattern="[a-zA-Z0-9_.-]+"
              maxLength={40}
              value={source}
              onChange={(e) => setSource(e.target.value.toLowerCase())}
            />
          </label>
          <label>
            Действует до (необязательно)
            <input
              type="datetime-local"
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
            />
          </label>
        </div>
        <fieldset>
          <legend>Разрешённые данные</legend>
          <div className="import-scopes">
            {entities.map((entity) => (
              <label key={entity}>
                <input
                  type="checkbox"
                  checked={scopes.includes(entity)}
                  onChange={(e) =>
                    setScopes(
                      e.target.checked
                        ? [...scopes, entity]
                        : scopes.filter((item) => item !== entity),
                    )
                  }
                />
                {entityLabels[entity]}
              </label>
            ))}
          </div>
        </fieldset>
        <button className="button primary" disabled={create.isPending || !scopes.length}>
          <KeyRound size={17} />
          Создать ключ
        </button>
      </form>
      <FormError error={create.error} />
      <FormError error={revoke.error} />
      {secret && (
        <div className="import-secret">
          <strong>Скопируйте ключ: он показывается только сейчас.</strong>
          <label>
            Новый ключ API
            <input readOnly value={secret} autoComplete="off" spellCheck={false} />
          </label>
          <button
            className="button secondary"
            onClick={() => {
              void navigator.clipboard
                .writeText(secret)
                .then(() => setCopied(true))
                .catch(() => setCopied(false));
            }}
          >
            <Copy size={16} />
            {copied ? 'Скопировано' : 'Скопировать'}
          </button>
          <button className="button secondary" onClick={() => setSecret('')}>
            Скрыть ключ
          </button>
        </div>
      )}
      {list.isPending ? (
        <Loading />
      ) : list.error ? (
        <ErrorState error={list.error} retry={() => void list.refetch()} />
      ) : (
        <div className="import-key-list">
          {list.data?.length === 0 && <p>Ключи ещё не созданы.</p>}
          {list.data?.map((key) => (
            <div key={key.id}>
              <div>
                <strong>{key.name}</strong>
                <p>
                  {key.source} · {key.prefix}… · {key.is_active ? 'Активен' : 'Отозван'}
                </p>
                <small>
                  {key.entities.map((entity) => entityLabels[entity]).join(', ')}
                  {key.expires_at && ` · до ${new Date(key.expires_at).toLocaleString('ru-RU')}`}
                  {key.last_used_at &&
                    ` · использован ${new Date(key.last_used_at).toLocaleString('ru-RU')}`}
                </small>
              </div>
              {key.is_active && (
                <button
                  className="button secondary compact"
                  disabled={revoke.isPending}
                  onClick={() => revoke.mutate(key.id)}
                >
                  Отозвать ключ «{key.name}»
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
function Api() {
  const { user } = useAuth();
  return (
    <>
      <section className="card import-panel">
        <h2>API для SAP и других систем</h2>
        <p>
          Внешняя система отправляет JSON по HTTPS с заголовком{' '}
          <code>Authorization: Bearer &lt;ключ&gt;</code>. Источник определяется ключом.
        </p>
        <dl className="import-endpoints">
          <dt>Проверка пакета</dt>
          <dd>
            <code>POST /api/integrations/validate</code>
          </dd>
          <dt>Импорт пакета</dt>
          <dd>
            <code>POST /api/integrations/imports</code>
          </dd>
        </dl>
        <p>
          В каждом пакете обязателен уникальный <code>request_id</code>. Повторная отправка того же
          пакета вернёт результат без повторных изменений. Объекты связываются по{' '}
          <code>external_id</code>. Передавайте отделы, команды, сотрудников и навыки вместе или
          отдельными пакетами.
        </p>
        <p>
          Для подключения SAP настройте отправку данных в показанный формат. Пример содержит отдел,
          начальника отдела, промежуточного руководителя, сотрудника, команду и навык.
        </p>
        <div className="import-actions">
          <a
            className="button secondary"
            href="/api/imports/example"
            download="hrm-integration-example.json"
          >
            <Download size={17} />
            Пример JSON
          </a>
          <a className="button secondary" href="/api/docs" target="_blank" rel="noreferrer">
            Документация API
          </a>
        </div>
        <p className="field-hint">
          До 10 000 записей. Пропущенные поля сохраняются, null очищает необязательное поле.
          Удаление записей и создание аккаунтов выполняются отдельно.
        </p>
      </section>
      {user?.role === 'admin' ? (
        <Keys />
      ) : (
        <section className="card import-panel">
          <p>
            Ключ доступа к API выдаёт администратор. Импорт файлов и журнал доступны вам в этом
            разделе.
          </p>
        </section>
      )}
    </>
  );
}
function Journal() {
  const list = useQuery({
    queryKey: ['import-history'],
    queryFn: () => request<ImportRun[]>('/imports/history'),
  });
  return (
    <section className="card import-panel">
      <h2>Журнал загрузок</h2>
      <p>Последние 50 загрузок через файлы и API.</p>
      {list.isPending ? (
        <Loading />
      ) : list.error ? (
        <ErrorState error={list.error} retry={() => void list.refetch()} />
      ) : !list.data?.length ? (
        <Empty title="Загрузок пока нет" description="Здесь появятся результаты импорта." />
      ) : (
        <div className="import-history">
          {list.data.map((run) => (
            <details key={run.id}>
              <summary>
                <span className={`import-run-status ${run.status}`}>
                  {run.status === 'success' ? 'Успешно' : 'Ошибка'}
                </span>
                <strong>{run.source}</strong>
                <span>
                  {run.channel === 'api' ? 'API' : 'Файл'} ·{' '}
                  {new Date(run.created_at).toLocaleString('ru-RU')}
                </span>
                <span>{run.result.total ?? 0} записей</span>
              </summary>
              <p>
                Запрос: {run.request_id} · инициатор: {run.actor_username}
              </p>
              <Counts result={run.result} />
              <Issues result={run.result} />
            </details>
          ))}
        </div>
      )}
    </section>
  );
}
export function ImportsPage() {
  const [tab, setTab] = useState('files');
  return (
    <>
      <PageHeader
        eyebrow="УПРАВЛЕНИЕ ДАННЫМИ"
        title="Импорт и интеграции"
        description="Загрузка сотрудников и структуры организации из файлов и внешних систем."
      />
      <div className="import-tabs" role="tablist" aria-label="Способ импорта">
        {[
          { id: 'files', name: 'Excel / CSV', Icon: FileUp },
          { id: 'api', name: 'API и ключи', Icon: Plug },
          { id: 'history', name: 'Журнал', Icon: History },
        ].map(({ id, name, Icon }) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            id={`import-tab-${id}`}
            aria-controls="import-content"
            className={`button ${tab === id ? 'primary' : 'secondary'}`}
            onClick={() => setTab(id)}
          >
            <Icon size={17} />
            {name}
          </button>
        ))}
      </div>
      <div id="import-content" role="tabpanel" aria-labelledby={`import-tab-${tab}`}>
        {tab === 'files' ? <Files /> : tab === 'api' ? <Api /> : <Journal />}
      </div>
    </>
  );
}
