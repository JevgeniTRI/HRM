import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { AlertCircle, ChevronLeft, ChevronRight, LoaderCircle, Search, X } from 'lucide-react';
import type { Employee, EmployeeStatus } from '../types';
import { initials, statusLabels } from '../lib/format';

export function Avatar({
  employee,
  size = 'normal',
}: {
  employee: Pick<Employee, 'first_name' | 'last_name'>;
  size?: 'normal' | 'large';
}) {
  const color = (employee.first_name.charCodeAt(0) + employee.last_name.charCodeAt(0)) % 5;
  return (
    <span className={`avatar avatar-${color} avatar-${size}`} aria-hidden="true">
      {initials(employee)}
    </span>
  );
}
export function StatusBadge({ status }: { status: EmployeeStatus }) {
  return (
    <span className={`status-badge status-${status}`}>
      <i />
      {statusLabels[status]}
    </span>
  );
}
export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="heading-actions">{children}</div>
    </div>
  );
}
export function Loading() {
  return (
    <div className="state-block" role="status">
      <LoaderCircle className="spin" size={24} />
      <span>Загружаем данные…</span>
    </div>
  );
}
export function ErrorState({ error, retry }: { error: Error | null; retry: () => void }) {
  return (
    <div className="state-block error-state" role="alert">
      <AlertCircle size={26} />
      <h3>Не удалось загрузить данные</h3>
      <p>{error?.message}</p>
      <button className="button secondary" onClick={retry}>
        Повторить
      </button>
    </div>
  );
}
export function Empty({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="state-block empty-state">
      <Search size={28} />
      <h3>{title}</h3>
      <p>{description}</p>
      {children}
    </div>
  );
}
export function FormError({ error }: { error: Error | null }) {
  return error ? (
    <p className="form-error" role="alert">
      <AlertCircle size={16} />
      {error.message}
    </p>
  ) : null;
}

export function Modal({
  title,
  subtitle,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const element = dialog.current;
    const previous = document.activeElement as HTMLElement | null;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    element?.showModal();
    return () => {
      element?.close();
      document.body.style.overflow = oldOverflow;
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      className={`modal ${wide ? 'modal-wide' : ''}`}
      aria-labelledby="modal-title"
      onCancel={(event) => {
        event.preventDefault();
        closeRef.current();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) closeRef.current();
      }}
    >
      <header className="modal-header">
        <div>
          <h2 id="modal-title">{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <button className="icon-button" aria-label="Закрыть" onClick={onClose}>
          <X size={20} />
        </button>
      </header>
      {children}
    </dialog>
  );
}

export function Pagination({
  page,
  total,
  pageSize,
  onChange,
}: {
  page: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="pagination">
      <span>
        {total
          ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} из ${total}`
          : '0 записей'}
      </span>
      <div>
        <button
          className="icon-button"
          aria-label="Предыдущая страница"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          <ChevronLeft size={18} />
        </button>
        <span>
          Страница {page} из {pages}
        </span>
        <button
          className="icon-button"
          aria-label="Следующая страница"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
        >
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}
