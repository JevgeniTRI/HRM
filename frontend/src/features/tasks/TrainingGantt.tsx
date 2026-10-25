import { useLayoutEffect, useRef } from 'react';
import type { CSSProperties } from 'react';
import { dateLabel, todayISO } from '../../lib/format';
import { calendarDays, calendarStatuses, dayISO, dayNumber, daysLabel } from './calendar';
import { decimalLabel } from './format';
import type { Task } from './types';

export function TrainingGantt({
  tasks,
  start,
  end,
  focusOn,
  focusRequest,
  scale,
  onVisibleDateChange,
  onSelect,
}: {
  tasks: Task[];
  start: number;
  end: number;
  focusOn: string;
  focusRequest: number;
  scale: 'month' | 'week';
  onVisibleDateChange: (date: string) => void;
  onSelect: (id: number) => void;
}) {
  const days = Array.from({ length: end - start + 1 }, (_, index) => dayISO(start + index));
  const today = todayISO();
  const months = days
    .filter((day) => day.endsWith('-01'))
    .map((iso) => {
      const monthStart = dayNumber(iso);
      const next = new Date(`${iso}T00:00:00Z`);
      next.setUTCMonth(next.getUTCMonth() + 1);
      return {
        iso,
        offset: monthStart - start + 1,
        length: Math.min(end + 1, next.getTime() / 86_400_000) - monthStart,
        label: monthLabel(iso),
      };
    });
  const gridStyle = { '--calendar-days': days.length } as CSSProperties;
  const scroll = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const element = scroll.current;
    if (!element) return;
    const chart = element.firstElementChild as HTMLElement;
    const labelWidth = parseFloat(
      getComputedStyle(chart).getPropertyValue('--calendar-label-width'),
    );
    const syncScroll = () => {
      const currentLabelWidth = parseFloat(
        getComputedStyle(chart).getPropertyValue('--calendar-label-width'),
      );
      const dayWidth = (element.scrollWidth - currentLabelWidth) / (end - start + 1);
      const limit = Math.max(0, element.scrollWidth - element.clientWidth);
      const position = Math.min(limit, Math.max(0, element.scrollLeft));
      const visibleFrom = dayISO(
        start + Math.min(end - start, Math.floor((position + 0.5) / dayWidth)),
      );
      onVisibleDateChange(visibleFrom);
    };
    const resize = () => {
      const width = parseFloat(getComputedStyle(chart).getPropertyValue('--calendar-label-width'));
      if (scale === 'week')
        chart.style.setProperty(
          '--calendar-day-width',
          `${Math.max(34, (element.clientWidth - width) / 7)}px`,
        );
      else chart.style.removeProperty('--calendar-day-width');
      syncScroll();
    };
    resize();
    const dayWidth = (element.scrollWidth - labelWidth) / (end - start + 1);
    element.scrollLeft = Math.max(0, (dayNumber(focusOn) - start) * dayWidth);
    syncScroll();
    element.addEventListener('scroll', syncScroll, { passive: true });
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    observer.observe(chart);
    return () => {
      element.removeEventListener('scroll', syncScroll);
      observer.disconnect();
    };
  }, [start, end, focusOn, focusRequest, scale, onVisibleDateChange]);
  function dayClass(iso: string) {
    const weekday = new Date(`${iso}T00:00:00Z`).getUTCDay();
    return `${weekday === 0 || weekday === 6 ? 'calendar-weekend' : ''} ${iso === today ? 'calendar-today' : ''}`;
  }
  return (
    <div
      ref={scroll}
      className="gantt-scroll"
      role="region"
      aria-label="Диаграмма Ганта обучений"
      tabIndex={0}
    >
      <div className="gantt-chart" style={gridStyle}>
        <div className="gantt-header">
          <div className="gantt-label gantt-header-label">
            Обучение <span>Период и длительность</span>
          </div>
          <div className="gantt-time-header">
            <div className="gantt-months">
              {months.map((month) => (
                <div
                  key={month.iso}
                  className="gantt-month"
                  style={{ gridColumn: `${month.offset} / span ${month.length}` }}
                >
                  <span>{month.label}</span>
                </div>
              ))}
            </div>
            <div className="gantt-days">
              {days.map((iso) => (
                <div key={iso} className={`gantt-day ${dayClass(iso)}`} aria-label={dateLabel(iso)}>
                  <small>
                    {new Date(`${iso}T12:00:00`).toLocaleDateString('ru-RU', {
                      weekday: 'short',
                    })}
                  </small>
                  <strong>{Number(iso.slice(8))}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
        {tasks.map((task) => {
          const first = dayNumber(task.start_on!);
          const last = dayNumber(task.end_on!);
          const left = Math.max(start, first);
          const right = Math.min(end, last);
          const period = `${dateLabel(task.start_on!)} — ${dateLabel(task.end_on!)}`;
          const duration = daysLabel(calendarDays(task.start_on!, task.end_on!));
          const hours =
            task.duration_hours !== null
              ? `${decimalLabel(task.duration_hours)} ч`
              : 'Часы не указаны';
          return (
            <div className="gantt-row" key={task.id}>
              <button
                className="gantt-label gantt-task-label"
                onClick={() => onSelect(task.id)}
                aria-label={`Открыть обучение ${task.title}`}
              >
                <strong title={task.title}>{task.title}</strong>
                <span>{period}</span>
                <small>
                  {duration} · {hours}
                </small>
              </button>
              <div className="gantt-track">
                <div className="gantt-grid" aria-hidden="true">
                  {days.map((iso) => (
                    <span key={iso} className={dayClass(iso)} />
                  ))}
                </div>
                <button
                  className={`gantt-bar gantt-bar-${task.status} ${first < start ? 'gantt-continues-left' : ''} ${last > end ? 'gantt-continues-right' : ''}`}
                  style={{
                    left: `${((left - start) / days.length) * 100}%`,
                    width: `${((right - left + 1) / days.length) * 100}%`,
                  }}
                  onClick={() => onSelect(task.id)}
                  aria-label={`Открыть сводку: ${task.title}`}
                  title={`${task.title}\n${period}\n${duration} · ${hours}\n${calendarStatuses[task.status]}`}
                >
                  <span>{task.title}</span>
                  <small>
                    {duration} · {hours}
                  </small>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function monthLabel(iso: string) {
  return new Date(`${iso}T12:00:00`).toLocaleDateString('ru-RU', {
    month: 'long',
    year: 'numeric',
  });
}
