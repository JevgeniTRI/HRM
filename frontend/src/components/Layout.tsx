import { useState } from 'react';
import {
  BookOpen,
  CalendarDays,
  Building2,
  ChevronRight,
  Columns3,
  Grid2X2,
  LayoutDashboard,
  Menu,
  Search,
  Users,
  X,
  ShieldCheck,
  UserRound,
  LockKeyhole,
  LogOut,
  Upload,
} from 'lucide-react';
import { useAuth, roleLabels } from '../lib/auth';
import { useMutation } from '@tanstack/react-query';
import { FormError } from './ui';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import type { FormEvent } from 'react';

const navigation = [
  { to: '/', label: 'Главная', icon: LayoutDashboard },
  { to: '/employees', label: 'Сотрудники', icon: Users },
  { to: '/teams', label: 'Команды', icon: Users },
  { to: '/tasks', label: 'Задачи и обучение', icon: Columns3 },
  { to: '/training-calendar', label: 'Календарь обучений', icon: CalendarDays },
  { to: '/skills', label: 'Навыки', icon: BookOpen },
  { to: '/matrix', label: 'Матрица навыков', icon: Grid2X2 },
  { to: '/departments', label: 'Подразделения', icon: Building2 },
  { to: '/imports', label: 'Импорт и интеграции', icon: Upload },
];

export function Layout() {
  const { user, globalAccess, logout } = useAuth();
  const signOut = useMutation({ mutationFn: logout });
  const menu = [
    ...(user?.employee_id
      ? [{ to: `/employees/${user.employee_id}`, label: 'Моя карточка-резюме', icon: UserRound }]
      : []),
    ...(globalAccess
      ? navigation
      : [
          ...(user?.role === 'manager'
            ? [
                { to: '/employees', label: 'Моя команда', icon: Building2 },
                { to: '/teams', label: 'Команды', icon: Users },
              ]
            : []),
          {
            to: '/tasks',
            label: user?.role === 'employee' ? 'Мои задачи' : 'Задачи команды',
            icon: Columns3,
          },
          { to: '/training-calendar', label: 'Календарь обучений', icon: CalendarDays },
        ]),
    ...(user?.role === 'admin'
      ? [{ to: '/accounts', label: 'Аккаунты и доступ', icon: ShieldCheck }]
      : []),
    { to: '/security', label: 'Безопасность', icon: LockKeyhole },
  ];
  const [mobileMenu, setMobileMenu] = useState(false);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const active =
    menu.find((item) => item.to === location.pathname)?.label ??
    (location.pathname.startsWith('/teams/') ? 'Карточка команды' : 'Карточка сотрудника');
  function submitSearch(event: FormEvent) {
    event.preventDefault();
    navigate(`/employees${search.trim() ? `?q=${encodeURIComponent(search.trim())}` : ''}`);
    setSearch('');
  }
  return (
    <div className="app-shell">
      {mobileMenu && (
        <button
          className="sidebar-backdrop"
          aria-label="Закрыть меню"
          onClick={() => setMobileMenu(false)}
        />
      )}
      <aside className={`sidebar ${mobileMenu ? 'is-open' : ''}`}>
        <Link to="/" className="brand" onClick={() => setMobileMenu(false)}>
          <img src="/favicon.svg" alt="" />
          <span>
            HRM<small>people & skills</small>
          </span>
        </Link>
        <div className="workspace-label">
          <span className="workspace-dot" />
          Рабочее пространство
        </div>
        <span className="navigation-label">УПРАВЛЕНИЕ КОМАНДОЙ</span>
        <nav aria-label="Основное меню">
          {menu.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setMobileMenu(false)}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <Icon size={19} strokeWidth={1.7} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span className="note-icon">
              <Users size={18} />
            </span>
            <h3>
              Команда начинается
              <br />с людей
            </h3>
            <p>
              Развивайте навыки.
              <br />
              Создавайте возможности.
            </p>
            <span className="note-line" />
          </div>
          <div className="sidebar-version">
            <span>HRM workspace</span>
            <span>v0.1</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="icon-button mobile-menu-button"
              onClick={() => setMobileMenu(!mobileMenu)}
              aria-label={mobileMenu ? 'Закрыть меню' : 'Открыть меню'}
            >
              {mobileMenu ? <X size={20} /> : <Menu size={20} />}
            </button>
            <span>Рабочее пространство</span>
            <ChevronRight size={14} />
            <strong>{active}</strong>
          </div>
          <div className="topbar-actions">
            {user?.role !== 'employee' && (
              <form className="global-search" onSubmit={submitSearch}>
                <Search size={17} />
                <input
                  aria-label="Найти сотрудника"
                  placeholder="Найти сотрудника…"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  maxLength={100}
                />
                <kbd>↵</kbd>
              </form>
            )}
            <div className="account-identity" title={roleLabels[user!.role]}>
              <strong>{user?.display_name}</strong>
              <small>{roleLabels[user!.role]}</small>
            </div>
            <div className="workspace-avatar" title={user?.display_name}>
              {user?.display_name.slice(0, 2).toUpperCase()}
            </div>
            <button
              className="icon-button"
              aria-label="Выйти"
              title="Выйти"
              disabled={signOut.isPending}
              onClick={() => signOut.mutate()}
            >
              <LogOut size={19} />
            </button>
          </div>
        </header>
        <main id="main-content">
          <FormError error={signOut.error} />
          <Outlet />
        </main>
        <footer className="page-footer">
          <span>HRM · Люди. Навыки. Развитие.</span>
          <span>
            <i />
            Всё начинается с команды
          </span>
        </footer>
      </div>
    </div>
  );
}
