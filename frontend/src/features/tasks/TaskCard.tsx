import {
  CalendarDays,
  Clock3,
  GripVertical,
  LoaderCircle,
  Pencil,
  Trash2,
  Users,
} from 'lucide-react';
import { dateLabel, todayISO } from '../../lib/format';
import {
  costLabel,
  decimalLabel,
  formatLabels,
  sourceLabels,
  taskStatuses,
  taskStatusLabels,
} from './format';
import type { Task, TaskStatus } from './types';
import { useAuth } from '../../lib/auth';

export interface CardActions {
  onEdit: (task: Task) => void;
  onDelete: (task: Task) => void;
  onMove: (task: Task, status: TaskStatus) => void;
  onDragStart: (task: Task) => void;
  onDragEnd: () => void;
}

export function TaskCard({
  task,
  pending,
  actions,
}: {
  task: Task;
  pending: boolean;
  actions: CardActions;
}) {
  const { user } = useAuth();
  const overdue = task.due_on && task.due_on < todayISO() && task.status !== 'done';
  return (
    <article
      className={`task-card ${pending ? 'task-saving' : ''}`}
      aria-label={`Задача: ${task.title}`}
      draggable={!pending}
      onDragStart={(event) => {
        event.dataTransfer.setData('application/x-hrm-task', String(task.id));
        event.dataTransfer.effectAllowed = 'move';
        actions.onDragStart(task);
      }}
      onDragEnd={actions.onDragEnd}
    >
      <div className="task-card-top">
        <span className="task-number">
          {pending ? <LoaderCircle size={13} className="spin" /> : <GripVertical size={14} />}#
          {String(task.id).padStart(3, '0')}
        </span>
        <div className="task-card-actions">
          <button
            className="icon-button"
            aria-label={`Редактировать задачу ${task.title}`}
            onClick={() => actions.onEdit(task)}
            disabled={pending}
          >
            <Pencil size={14} />
          </button>
          {user?.role !== 'employee' && (
            <button
              className="icon-button"
              aria-label={`Удалить задачу ${task.title}`}
              onClick={() => actions.onDelete(task)}
              disabled={pending}
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>
      <button className="task-title" onClick={() => actions.onEdit(task)} disabled={pending}>
        <h3>{task.title}</h3>
      </button>
      {task.description && <p className="task-description">{task.description}</p>}
      {task.assignee_name && <p className="task-assignee">Исполнитель: {task.assignee_name}</p>}
      <div className="task-tags">
        {task.learning_source ? (
          <>
            <span className={`task-tag task-source-${task.learning_source}`}>
              {sourceLabels[task.learning_source]}
            </span>
            {task.learning_format && (
              <span className="task-tag task-format">{formatLabels[task.learning_format]}</span>
            )}
          </>
        ) : (
          <span className="task-tag task-ordinary">Обычная задача</span>
        )}
      </div>
      {task.departments.length > 0 && (
        <div className="task-departments">
          {task.departments.map((dept) => (
            <span key={dept.id}>{dept.name}</span>
          ))}
        </div>
      )}
      {task.learning_source && (
        <div className="task-training-meta">
          <span>
            <Users size={14} />
            {task.participant_count} участников
          </span>
          <span>
            <Clock3 size={14} />
            {task.duration_hours !== null
              ? `${decimalLabel(task.duration_hours)} ч`
              : 'Длительность не указана'}
          </span>
        </div>
      )}
      {(task.person_hours !== null || task.cost !== null) && (
        <div className="task-totals">
          {task.person_hours !== null && (
            <div>
              <small>ЧЕЛОВЕКОЧАСЫ</small>
              <strong>
                {decimalLabel(task.person_hours)} <span>чел·ч</span>
              </strong>
            </div>
          )}
          {task.cost !== null && task.currency && (
            <div>
              <small>СТОИМОСТЬ ВСЕГО</small>
              <strong>{costLabel(task.cost, task.currency)}</strong>
            </div>
          )}
        </div>
      )}
      <div className="task-card-bottom">
        <span className={`task-due ${overdue ? 'overdue' : ''}`}>
          {task.due_on ? (
            <>
              <CalendarDays size={13} />
              {dateLabel(task.due_on)}
              {overdue && ' · Просрочено'}
            </>
          ) : (
            'Без срока'
          )}
        </span>
        <select
          aria-label={`Статус задачи ${task.title}`}
          value={task.status}
          disabled={pending}
          onChange={(event) => actions.onMove(task, event.target.value as TaskStatus)}
        >
          {taskStatuses.map((status) => (
            <option key={status} value={status}>
              {taskStatusLabels[status]}
            </option>
          ))}
        </select>
      </div>
    </article>
  );
}
