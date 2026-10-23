import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { request } from '../lib/api';
import { useAuth } from '../lib/auth';
import { FormError, PageHeader } from '../components/ui';

export function PasswordPage() {
  const auth = useAuth();
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [repeat, setRepeat] = useState('');
  const save = useMutation({
    mutationFn: () =>
      request('/auth/password', {
        method: 'PUT',
        body: JSON.stringify({ current_password: current, new_password: password }),
      }),
    onSuccess: () => window.dispatchEvent(new Event('hrm-session-expired')),
  });
  return (
    <>
      <PageHeader
        title="Безопасность аккаунта"
        description={`${auth.user?.username} · после смены пароля войдите снова.`}
      />
      <section className="card account-password-card">
        <form
          className="modal-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (!save.isPending && password === repeat) save.mutate();
          }}
        >
          <label>
            Текущий пароль
            <input
              type="password"
              required
              autoComplete="current-password"
              maxLength={128}
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </label>
          <label>
            Новый пароль
            <input
              type="password"
              required
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <label>
            Повторите новый пароль
            <input
              type="password"
              required
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              value={repeat}
              onChange={(e) => setRepeat(e.target.value)}
            />
          </label>
          {repeat && repeat !== password && (
            <p role="alert" className="field-hint">
              Пароли не совпадают.
            </p>
          )}
          <p className="field-hint">От 12 до 128 символов. Все текущие сеансы будут завершены.</p>
          <FormError error={save.error} />
          <button className="button primary" disabled={save.isPending || password !== repeat}>
            {save.isPending ? 'Сохраняем…' : 'Изменить пароль'}
          </button>
        </form>
      </section>
    </>
  );
}
