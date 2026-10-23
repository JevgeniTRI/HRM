import type { Employee, EmployeeStatus } from '../types';

export const statusLabels: Record<EmployeeStatus, string> = {
  active: 'Работает',
  probation: 'Испытательный срок',
  leave: 'В отпуске',
  inactive: 'Неактивен',
};
export const fullName = (employee: Pick<Employee, 'first_name' | 'last_name'>) =>
  `${employee.first_name} ${employee.last_name}`;
export const initials = (employee: Pick<Employee, 'first_name' | 'last_name'>) =>
  `${employee.first_name[0] ?? ''}${employee.last_name[0] ?? ''}`;
export const dateLabel = (date: string) =>
  new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' }).format(
    new Date(`${date}T12:00:00`),
  );
export const timestamp = (date: string) =>
  new Date(/[zZ]|[+-]\d\d:\d\d$/.test(date) ? date : `${date}Z`);
export function activityTime(date: string) {
  const value = timestamp(date);
  const days = Math.floor((Date.now() - value.getTime()) / 86400000);
  if (days === 0)
    return `Сегодня, ${value.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
  if (days === 1) return 'Вчера';
  return value.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' });
}
export function todayISO() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
export const levelLabels = [
  'Нет опыта',
  'Начальный',
  'Базовый',
  'Уверенный',
  'Продвинутый',
  'Эксперт',
];
