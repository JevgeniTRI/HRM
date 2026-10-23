import { useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Columns3, Info, Plus, X } from 'lucide-react';
import { DeleteDialog } from '../components/CatalogForm';
import { FormError, PageHeader } from '../components/ui';
import { taskApi } from '../features/tasks/api';
import { taskStatuses } from '../features/tasks/format';
import { KanbanColumn } from '../features/tasks/KanbanColumn';
import { TaskFilters, useTaskFilters } from '../features/tasks/TaskFilters';
import { TaskForm } from '../features/tasks/TaskForm';
import { TaskSummaryCards } from '../features/tasks/TaskSummaryCards';
import { useTaskMoves } from '../features/tasks/useTaskMoves';
import type { Task, TaskStatus } from '../features/tasks/types';
import '../features/tasks/tasks.css';

export function TasksPage() {
  const filters = useTaskFilters();
  const summary = useQuery({
    queryKey: ['tasks', 'summary', filters],
    queryFn: () => taskApi.summary(filters),
  });
  const [form, setForm] = useState<{ task?: Task; status: TaskStatus } | null>(null);
  const [remove, setRemove] = useState<Task | null>(null);
  const dragged = useRef<Task | null>(null);
  const { moves, move, error, clearError } = useTaskMoves();
  const actions = {
    onEdit: (task: Task) => setForm({ task, status: task.status }),
    onDelete: setRemove,
    onMove: move,
    onDragStart: (task: Task) => {
      dragged.current = task;
    },
    onDragEnd: () => {
      dragged.current = null;
    },
  };
  function drop(status: TaskStatus, id: string) {
    const task = dragged.current;
    if (task && String(task.id) === id) move(task, status);
    dragged.current = null;
  }
  return (
    <>
      <PageHeader
        eyebrow="ЗАДАЧИ И РАЗВИТИЕ"
        title="Kanban-доска"
        description="От идеи до результата. Планируйте задачи и обучение команды."
      >
        <button className="button primary" onClick={() => setForm({ status: 'todo' })}>
          <Plus size={18} />
          Создать задачу
        </button>
      </PageHeader>
      <TaskFilters />
      <TaskSummaryCards
        summary={summary.data}
        loading={summary.isPending}
        error={summary.error}
        retry={() => summary.refetch()}
      />
      <div className="board-caption">
        <span>
          <Columns3 size={16} />
          To Do → In Progress → Done
        </span>
        <span>
          {moves.length ? 'Сохраняем статус…' : 'Перетащите карточку или выберите статус'}
        </span>
      </div>
      {error && (
        <div className="board-error">
          <FormError error={error} />
          <button
            className="icon-button"
            aria-label="Закрыть ошибку перемещения"
            onClick={clearError}
          >
            <X size={17} />
          </button>
        </div>
      )}
      <div className="kanban-board">
        {taskStatuses.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            filters={filters}
            moves={moves}
            actions={actions}
            onCreate={(status) => setForm({ status })}
            onDrop={drop}
          />
        ))}
      </div>
      <div className="info-note task-board-note">
        <Info size={18} />
        <p>
          Человекочасы = длительность × число участников. Сводка включает все статусы и учитывает
          фильтры. Длительность и стоимость можно заполнить позже; суммы в разных валютах
          показываются отдельно.
        </p>
      </div>
      {form && <TaskForm task={form.task} status={form.status} onClose={() => setForm(null)} />}
      {remove && (
        <DeleteDialog
          title="Удалить задачу?"
          description={`Карточка «${remove.title}» будет удалена с доски. Действие нельзя отменить.`}
          onDelete={() => taskApi.delete(remove)}
          onClose={() => setRemove(null)}
        />
      )}
    </>
  );
}
