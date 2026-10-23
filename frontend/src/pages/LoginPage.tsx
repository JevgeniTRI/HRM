import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { LockKeyhole } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { FormError } from '../components/ui';

export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const login = useMutation({
    mutationFn: () => auth.login(username, password),
    onSuccess: () => navigate('/', { replace: true }),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!login.isPending) login.mutate();
  }
  return (
    <main className="auth-screen">
      <section className="card auth-card">
        <a className="brand" href="/">
          <img src="/favicon.svg" alt="" />
          <span>
            HRM<small>people & skills</small>
          </span>
        </a>
        <div className="auth-heading">
          <LockKeyhole size={24} />
          <h1>Вход в рабочее пространство</h1>
          <p>Ваша команда, задачи и развитие.</p>
        </div>
        <form className="modal-form" onSubmit={submit}>
          <label>
            Логин
            <input
              name="username"
              autoComplete="username"
              autoFocus
              required
              maxLength={80}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label>
            Пароль
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <FormError error={login.error} />
          <button className="button primary" disabled={login.isPending}>
            {login.isPending ? 'Входим…' : 'Войти'}
          </button>
        </form>
        <p className="field-hint">Для получения доступа обратитесь к администратору.</p>
      </section>
    </main>
  );
}
