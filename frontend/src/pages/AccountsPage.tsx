import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Pencil, Plus, ShieldCheck } from 'lucide-react';
import { request } from '../lib/api';
import { roleLabels, useAuth } from '../lib/auth';
import type { Account, Role } from '../lib/auth';
import { Empty, ErrorState, FormError, Loading, Modal, PageHeader } from '../components/ui';
import { EmployeePicker } from '../components/EmployeePicker';

function AccountForm({ account, onClose }: { account?: Account; onClose: () => void }) {
  const auth = useAuth();
  const cache = useQueryClient();
  const [username, setUsername] = useState(account?.username ?? '');
  const [role, setRole] = useState<Role>(account?.role ?? 'employee');
  const [employeeId, setEmployeeId] = useState<number | null>(account?.employee_id ?? null);
  const [active, setActive] = useState(account?.is_active ?? true);
  const [password, setPassword] = useState('');
  const save = useMutation({
    mutationFn: () =>
      request(`/accounts${account ? `/${account.id}` : ''}`, {
        method: account ? 'PUT' : 'POST',
        body: JSON.stringify({
          username,
          role,
          employee_id: employeeId,
          is_active: active,
          ...(!account ? { password } : {}),
        }),
      }),
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ['accounts'] });
      onClose();
      if (account?.id === auth.user?.id) window.dispatchEvent(new Event('hrm-session-expired'));
    },
  });
  const own = account?.id === auth.user?.id;
  return (
    <Modal
      title={account ? 'Редактировать аккаунт' : 'Новый аккаунт'}
      subtitle="Свяжите доступ с карточкой сотрудника и назначьте роль."
      onClose={() => {
        if (!save.isPending) onClose();
      }}
    >
      <form
        className="modal-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (!save.isPending) save.mutate();
        }}
      >
        <label>
          Логин
          <input
            autoFocus
            required
            autoComplete="off"
            minLength={3}
            maxLength={80}
            pattern="[a-zA-Z0-9_.@+\-]+"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <p className="field-hint">Латинские буквы, цифры и символы _ . @ + -</p>
        <label>
          Роль
          <select value={role} disabled={own} onChange={(e) => setRole(e.target.value as Role)}>
            {Object.entries(roleLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <EmployeePicker
          value={employeeId}
          onChange={setEmployeeId}
          required={role !== 'admin'}
          label="Карточка сотрудника"
        />
        <p className="field-hint">
          Руководитель получает доступ к отделу выбранного сотрудника. Один аккаунт на сотрудника.
        </p>
        {!account && (
          <label>
            Начальный пароль
            <input
              type="password"
              required
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <span className="field-hint">Не менее 12 символов.</span>
          </label>
        )}
        <label className="account-active">
          <input
            type="checkbox"
            checked={active}
            disabled={own}
            onChange={(e) => setActive(e.target.checked)}
          />
          Аккаунт активен
        </label>
        {account && (
          <p className="field-hint">Изменения завершат текущие сеансы этого пользователя.</p>
        )}
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
          <button className="button primary" disabled={save.isPending}>
            {save.isPending ? 'Сохраняем…' : account ? 'Сохранить' : 'Создать аккаунт'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ResetPassword({ account, onClose }: { account: Account; onClose: () => void }) {
  const auth = useAuth();
  const [password, setPassword] = useState('');
  const save = useMutation({
    mutationFn: () =>
      request(`/accounts/${account.id}/password`, {
        method: 'PUT',
        body: JSON.stringify({ password }),
      }),
    onSuccess: () => {
      onClose();
      if (account.id === auth.user?.id) window.dispatchEvent(new Event('hrm-session-expired'));
    },
  });
  return (
    <Modal
      title={`Новый пароль · ${account.username}`}
      subtitle="Текущие сеансы пользователя будут завершены."
      onClose={() => {
        if (!save.isPending) onClose();
      }}
    >
      <form
        className="modal-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (!save.isPending) save.mutate();
        }}
      >
        <label>
          Новый пароль
          <input
            autoFocus
            type="password"
            autoComplete="new-password"
            required
            minLength={12}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
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
          <button className="button primary" disabled={save.isPending}>
            {save.isPending ? 'Сохраняем…' : 'Установить пароль'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function AccountsPage() {
  const accounts = useQuery({
    queryKey: ['accounts'],
    queryFn: () => request<Account[]>('/accounts'),
  });
  const [form, setForm] = useState<Account | 'new' | null>(null);
  const [reset, setReset] = useState<Account | null>(null);
  return (
    <>
      <PageHeader
        title="Аккаунты и доступ"
        description="Управляйте ролями, входом и привязкой к сотрудникам."
      >
        <button className="button primary" onClick={() => setForm('new')}>
          <Plus size={18} />
          Создать аккаунт
        </button>
      </PageHeader>
      <section className="card">
        <div className="card-heading">
          <h2>
            <ShieldCheck size={20} /> Пользователи системы{' '}
            <span className="count-tag">{accounts.data?.length ?? '—'}</span>
          </h2>
        </div>
        {accounts.isPending ? (
          <Loading />
        ) : accounts.isError ? (
          <ErrorState error={accounts.error} retry={() => accounts.refetch()} />
        ) : !accounts.data.length ? (
          <Empty title="Аккаунтов пока нет" description="Создайте первый аккаунт сотрудника." />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Логин</th>
                  <th>Роль</th>
                  <th>Карточка сотрудника</th>
                  <th>Доступ</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {accounts.data.map((account) => (
                  <tr key={account.id}>
                    <td>
                      <strong>{account.username}</strong>
                    </td>
                    <td>{roleLabels[account.role]}</td>
                    <td>
                      {account.employee_id ? (
                        <a href={`/employees/${account.employee_id}`}>
                          Открыть карточку #{account.employee_id}
                        </a>
                      ) : (
                        'Не привязан'
                      )}
                    </td>
                    <td>
                      <span className={`status-badge ${account.is_active ? 'active' : 'inactive'}`}>
                        {account.is_active ? 'Активен' : 'Отключён'}
                      </span>
                    </td>
                    <td>
                      <div className="account-actions">
                        <button
                          className="icon-button"
                          aria-label={`Редактировать аккаунт ${account.username}`}
                          onClick={() => setForm(account)}
                        >
                          <Pencil size={17} />
                        </button>
                        <button
                          className="icon-button"
                          aria-label={`Сменить пароль ${account.username}`}
                          onClick={() => setReset(account)}
                        >
                          <KeyRound size={17} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {form && (
        <AccountForm account={form === 'new' ? undefined : form} onClose={() => setForm(null)} />
      )}
      {reset && <ResetPassword account={reset} onClose={() => setReset(null)} />}
    </>
  );
}
