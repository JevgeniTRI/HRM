import type { TaskStatus } from './types';

const DAY_MS = 86_400_000;

export const calendarStatuses: Record<TaskStatus, string> = {
  todo: 'Запланировано',
  in_progress: 'В процессе',
  done: 'Завершено',
};

// Compare calendar dates in UTC so daylight-saving changes do not shift bars.
export const dayNumber = (iso: string) => Date.parse(`${iso}T00:00:00Z`) / DAY_MS;
export const dayISO = (day: number) => new Date(day * DAY_MS).toISOString().slice(0, 10);
export const calendarDays = (start: string, end: string) => dayNumber(end) - dayNumber(start) + 1;
export const daysLabel = (count: number) =>
  `${count} ${count % 10 === 1 && count % 100 !== 11 ? 'день' : count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 12 || count % 100 > 14) ? 'дня' : 'дней'}`;

export function calendarRange(anchor: string, scale: 'month' | 'week') {
  const date = new Date(`${anchor}T00:00:00Z`);
  if (scale === 'month') {
    const start = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1) / DAY_MS;
    const end = Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0) / DAY_MS;
    return { start, end };
  }
  const start = dayNumber(anchor) - ((date.getUTCDay() + 6) % 7);
  return { start, end: start + 6 };
}

export function calendarYear(anchor: string) {
  const year = anchor.slice(0, 4);
  return { start: dayNumber(`${year}-01-01`), end: dayNumber(`${year}-12-31`) };
}

export function shiftCalendar(anchor: string, scale: 'month' | 'week', direction: number) {
  if (scale === 'week') return dayISO(dayNumber(anchor) + direction * 7);
  const date = new Date(`${anchor}T00:00:00Z`);
  return dayISO(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + direction, 1) / DAY_MS);
}
