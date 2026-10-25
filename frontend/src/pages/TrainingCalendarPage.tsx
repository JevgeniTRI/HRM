import { useState } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { CalendarDays, ChevronLeft, ChevronRight, Plus, Search } from 'lucide-react';
import { Empty, ErrorState, FormError, Loading, PageHeader } from '../components/ui';
import { taskApi } from '../features/tasks/api';
import {
  calendarRange,
  calendarYear,
  calendarStatuses,
  dayISO,
  shiftCalendar,
} from '../features/tasks/calendar';
import { decimalLabel } from '../features/tasks/format';
import { TaskForm } from '../features/tasks/TaskForm';
import { TrainingGantt } from '../features/tasks/TrainingGantt';
import { TrainingSummary } from '../features/tasks/TrainingSummary';
import type { Task } from '../features/tasks/types';
import { dateLabel, todayISO } from '../lib/format';
import { useDepartments } from '../lib/queries';
import { useDebouncedValue } from '../lib/useDebouncedValue';
import '../features/tasks/tasks.css';
import '../features/tasks/calendar.css';

export function TrainingCalendarPage() {
  const [focus, setFocus] = useState(() => ({ date: todayISO(), request: 0 }));
  const [viewDate, setViewDate] = useState(todayISO);
  const anchor = focus.date;
  const [scale, setScale] = useState<'month' | 'week'>('month');
  const [search, setSearch] = useState('');
  const [department, setDepartment] = useState('');
  const [selected, setSelected] = useState<number | null>(null);
  const [form, setForm] = useState<{ task?: Task } | null>(null);
  const departments = useDepartments();
  const q = useDebouncedValue(search);
  const { start, end } = calendarYear(anchor);
  const from = dayISO(start);
  const to = dayISO(end);
  const filters = { q, department_id: department };
  const query = useInfiniteQuery({
    queryKey: ['tasks', 'calendar', from, to, filters],
    queryFn: ({ pageParam }) => taskApi.calendar(from, to, filters, pageParam),
    initialPageParam: 1,
    getNextPageParam: (page) =>
      page.page * page.page_size < page.total ? page.page + 1 : undefined,
  });
  const tasks = query.data?.pages.flatMap((page) => page.items) ?? [];
  const scheduled = tasks.filter((task) => task.start_on && task.end_on);
  const unscheduled = tasks.filter((task) => !task.start_on);
  const total = query.data?.pages[0].total ?? 0;
  const period =
    scale === 'month'
      ? new Date(`${viewDate}T12:00:00`).toLocaleDateString('ru-RU', {
          month: 'long',
          year: 'numeric',
        })
      : `${dateLabel(dayISO(calendarRange(viewDate, 'week').start))} — ${dateLabel(dayISO(calendarRange(viewDate, 'week').end))}`;
  function jumpTo(date: string) {
    setViewDate(date);
    setFocus((previous) => ({ date, request: previous.request + 1 }));
  }
  function edit(task: Task) {
    setSelected(null);
    setForm({ task });
  }
  return (
    <>
      <PageHeader
        eyebrow="ПЛАНИРОВАНИЕ И РАЗВИТИЕ"
        title="Календарь обучений"
        description="Начало, окончание и длительность обучений на одной временной шкале."
      >
        <button className="button primary" onClick={() => setForm({})}>
          <Plus size={18} />
          Добавить обучение
        </button>
      </PageHeader>
      <section className="training-calendar" aria-label="Календарь обучений">
        <div className="calendar-toolbar">
          <div className="calendar-period-controls">
            <button
              className="icon-button"
              aria-label="Предыдущий период"
              onClick={() => jumpTo(shiftCalendar(viewDate, scale, -1))}
            >
              <ChevronLeft size={19} />
            </button>
            <h2 aria-live="polite">{period}</h2>
            <button
              className="icon-button"
              aria-label="Следующий период"
              onClick={() => jumpTo(shiftCalendar(viewDate, scale, 1))}
            >
              <ChevronRight size={19} />
            </button>
            <button className="button secondary compact" onClick={() => jumpTo(todayISO())}>
              Сегодня
            </button>
          </div>
          <div className="calendar-view-controls">
            <label className="calendar-date-picker">
              Перейти к дате
              <input
                aria-label="Дата календаря"
                type="date"
                value={viewDate}
                onChange={(event) => {
                  if (event.target.value) jumpTo(event.target.value);
                }}
              />
            </label>
            <label>
              Масштаб
              <select
                aria-label="Масштаб календаря"
                value={scale}
                onChange={(event) => {
                  jumpTo(viewDate);
                  setScale(event.target.value as 'month' | 'week');
                }}
              >
                <option value="month">Месяц</option>
                <option value="week">Неделя</option>
              </select>
            </label>
          </div>
        </div>
        <div className="calendar-filters">
          <label className="calendar-search">
            <Search size={17} />
            <input
              aria-label="Поиск обучений"
              placeholder="Найти обучение…"
              maxLength={100}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <select
            aria-label="Подразделение обучения"
            value={department}
            onChange={(event) => setDepartment(event.target.value)}
            disabled={departments.isPending || departments.isError}
          >
            <option value="">Все доступные подразделения</option>
            {departments.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          {(search || department) && (
            <button
              className="button secondary compact"
              onClick={() => {
                setSearch('');
                setDepartment('');
              }}
            >
              Сбросить
            </button>
          )}
          {departments.isError && (
            <div>
              <FormError error={departments.error} />
              <button className="button secondary compact" onClick={() => departments.refetch()}>
                Повторить загрузку подразделений
              </button>
            </div>
          )}
        </div>
        <div className="calendar-caption">
          <span>
            <CalendarDays size={16} />
            {tasks.length} из {total} обучений · нажмите на полосу, чтобы открыть сводку
          </span>
          <div className="calendar-legend">
            {(['todo', 'in_progress', 'done'] as const).map((status) => (
              <span key={status} className={`calendar-status calendar-status-${status}`}>
                <i />
                {calendarStatuses[status]}
              </span>
            ))}
          </div>
        </div>
        {query.isPending ? (
          <Loading />
        ) : query.isError && !query.data ? (
          <ErrorState error={query.error} retry={() => query.refetch()} />
        ) : (
          <>
            <TrainingGantt
              tasks={scheduled}
              start={start}
              end={end}
              focusOn={anchor}
              focusRequest={focus.request}
              scale={scale}
              onVisibleDateChange={setViewDate}
              onSelect={setSelected}
            />
            {!scheduled.length && (
              <Empty
                title="В этом году нет запланированных обучений"
                description="Выберите другой год или задайте даты обучения в карточке."
              />
            )}
            {unscheduled.length > 0 && (
              <div className="calendar-unscheduled">
                <div className="calendar-unscheduled-heading">
                  <h3>
                    Без назначенных дат <span>{unscheduled.length}</span>
                  </h3>
                  <p>Укажите период проведения, чтобы обучение появилось на диаграмме.</p>
                </div>
                {unscheduled.map((task) => (
                  <div className="calendar-unscheduled-row" key={task.id}>
                    <button
                      className="calendar-unscheduled-title"
                      onClick={() => setSelected(task.id)}
                    >
                      <strong>{task.title}</strong>
                      <span>
                        {task.departments.map((item) => item.name).join(', ') ||
                          'Подразделение не выбрано'}{' '}
                        ·{' '}
                        {task.duration_hours !== null
                          ? `${decimalLabel(task.duration_hours)} ч`
                          : 'Длительность не указана'}
                      </span>
                    </button>
                    <span className={`calendar-status calendar-status-${task.status}`}>
                      <i />
                      {calendarStatuses[task.status]}
                    </span>
                    <button
                      className="button secondary compact"
                      aria-label={`Назначить даты: ${task.title}`}
                      onClick={() => edit(task)}
                    >
                      Назначить даты
                    </button>
                  </div>
                ))}
              </div>
            )}
            {query.isError && <FormError error={query.error} />}
            {query.hasNextPage && (
              <div className="calendar-load-more">
                <button
                  className="button secondary"
                  disabled={query.isFetchingNextPage}
                  onClick={() => query.fetchNextPage()}
                >
                  {query.isFetchingNextPage ? 'Загружаем…' : 'Показать ещё обучения'}
                </button>
              </div>
            )}
          </>
        )}
      </section>
      {selected !== null && (
        <TrainingSummary taskId={selected} onClose={() => setSelected(null)} onEdit={edit} />
      )}
      {form && <TaskForm task={form.task} trainingOnly onClose={() => setForm(null)} />}
    </>
  );
}
