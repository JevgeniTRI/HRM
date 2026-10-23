import { useState } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { Check, Circle, Clock3, Plus } from 'lucide-react';
import { ErrorState, Loading } from '../../components/ui';
import { taskApi } from './api';
import { taskStatusLabels } from './format';
import { TaskCard } from './TaskCard';
import type { CardActions } from './TaskCard';
import type { PendingMove, Task, TaskFilters, TaskStatus } from './types';

interface ColumnProps {
  status: TaskStatus;
  filters: TaskFilters;
  moves: PendingMove[];
  actions: CardActions;
  onCreate: (status: TaskStatus) => void;
  onDrop: (status: TaskStatus, id: string) => void;
}

export function KanbanColumn({ status, filters, moves, actions, onCreate, onDrop }: ColumnProps) {
  const [over, setOver] = useState(false);
  const tasks = useInfiniteQuery({
    queryKey: ['tasks', 'column', status, filters],
    queryFn: ({ pageParam }) => taskApi.list(filters, status, pageParam),
    initialPageParam: 1,
    getNextPageParam: (last) =>
      last.page * last.page_size < last.total ? last.page + 1 : undefined,
  });
  const cached = tasks.data?.pages.flatMap((page) => page.items) ?? [];
  const movingIds = new Set(moves.map((move) => move.task.id));
  const incoming: Task[] = moves
    .filter((move) => move.status === status)
    .map((move) => ({ ...move.task, status }));
  const visible = [...incoming, ...cached.filter((task) => !movingIds.has(task.id))];
  const Icon = status === 'todo' ? Circle : status === 'in_progress' ? Clock3 : Check;
  return (
    <section
      className={`kanban-column column-${status} ${over ? 'is-drop-target' : ''}`}
      aria-label={taskStatusLabels[status]}
      onDragOver={(event) => {
        if (event.dataTransfer.types.includes('application/x-hrm-task')) {
          event.preventDefault();
          event.dataTransfer.dropEffect = 'move';
          setOver(true);
        }
      }}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOver(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        onDrop(status, event.dataTransfer.getData('application/x-hrm-task'));
      }}
    >
      <header className="kanban-column-heading">
        <h2>
          <span className="column-state-icon">
            <Icon size={16} />
          </span>
          {taskStatusLabels[status]}
          <span className="column-count">{tasks.data?.pages[0]?.total ?? '—'}</span>
        </h2>
        <button
          className="icon-button"
          aria-label={`Добавить задачу в ${taskStatusLabels[status]}`}
          onClick={() => onCreate(status)}
        >
          <Plus size={18} />
        </button>
      </header>
      <div className="kanban-column-body">
        {tasks.isPending ? (
          <Loading />
        ) : tasks.isError ? (
          <ErrorState error={tasks.error} retry={() => tasks.refetch()} />
        ) : (
          <>
            {visible.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                pending={movingIds.has(task.id)}
                actions={actions}
              />
            ))}
            {!visible.length && (
              <div className="kanban-empty">
                <Icon size={24} />
                <strong>Пока нет задач</strong>
                <p>Создайте задачу или перенесите её сюда</p>
                <button onClick={() => onCreate(status)}>
                  <Plus size={14} />
                  Добавить задачу
                </button>
              </div>
            )}
            {tasks.hasNextPage && (
              <button
                className="button secondary load-more-tasks"
                disabled={tasks.isFetchingNextPage}
                onClick={() => tasks.fetchNextPage()}
              >
                {tasks.isFetchingNextPage ? 'Загружаем…' : 'Показать ещё'}
              </button>
            )}
          </>
        )}
      </div>
    </section>
  );
}
