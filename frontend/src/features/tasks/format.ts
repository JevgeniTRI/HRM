import type { TaskStatus } from './types';

export const taskStatuses: TaskStatus[] = ['todo', 'in_progress', 'done'];
export const taskStatusLabels: Record<TaskStatus, string> = {
  todo: 'To Do',
  in_progress: 'In Progress',
  done: 'Done',
};
export const sourceLabels = { internal: 'Внутреннее', external: 'Внешнее' };
export const formatLabels = { individual: 'Индивидуальное', group: 'Групповое' };
export const decimalLabel = (value: string) =>
  new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(value));
export const costLabel = (value: string, currency: string) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency, maximumFractionDigits: 2 }).format(
    Number(value),
  );
