import { useQuery } from '@tanstack/react-query';
import { Pencil } from 'lucide-react';
import { ErrorState, Loading, Modal } from '../../components/ui';
import { dateLabel } from '../../lib/format';
import { taskApi } from './api';
import { calendarDays, calendarStatuses, daysLabel } from './calendar';
import { costLabel, decimalLabel, formatLabels, sourceLabels } from './format';
import type { Task } from './types';

export function TrainingSummary({
  taskId,
  onClose,
  onEdit,
}: {
  taskId: number;
  onClose: () => void;
  onEdit: (task: Task) => void;
}) {
  const query = useQuery({
    queryKey: ['tasks', 'detail', taskId],
    queryFn: () => taskApi.read(taskId),
  });
  const task = query.data;
  return (
    <Modal
      title={task?.title ?? 'Сводка обучения'}
      subtitle="Сводка обучения"
      onClose={onClose}
      wide
    >
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => query.refetch()} />
      ) : task ? (
        <div className="training-summary">
          <span className={`calendar-status calendar-status-${task.status}`}>
            <i />
            {calendarStatuses[task.status]}
          </span>
          <p className="training-summary-description">
            {task.description || 'Описание не добавлено.'}
          </p>
          <dl className="training-summary-grid">
            <div>
              <dt>Начало обучения</dt>
              <dd>{task.start_on ? dateLabel(task.start_on) : 'Не указано'}</dd>
            </div>
            <div>
              <dt>Окончание обучения</dt>
              <dd>{task.end_on ? dateLabel(task.end_on) : 'Не указано'}</dd>
            </div>
            <div>
              <dt>Календарный период</dt>
              <dd>
                {task.start_on && task.end_on
                  ? daysLabel(calendarDays(task.start_on, task.end_on))
                  : 'Не назначен'}
              </dd>
            </div>
            <div>
              <dt>Длительность обучения</dt>
              <dd>
                {task.duration_hours !== null
                  ? `${decimalLabel(task.duration_hours)} ч`
                  : 'Не указана'}
              </dd>
            </div>
            <div>
              <dt>Источник</dt>
              <dd>{task.learning_source ? sourceLabels[task.learning_source] : '—'}</dd>
            </div>
            <div>
              <dt>Формат</dt>
              <dd>{task.learning_format ? formatLabels[task.learning_format] : '—'}</dd>
            </div>
            <div>
              <dt>Участники</dt>
              <dd>{task.participant_count ?? 'Не указаны'}</dd>
            </div>
            <div>
              <dt>Трудоёмкость</dt>
              <dd>
                {task.person_hours !== null
                  ? `${decimalLabel(task.person_hours)} чел·ч`
                  : 'Не указана'}
              </dd>
            </div>
            <div>
              <dt>Стоимость всего</dt>
              <dd>
                {task.cost !== null && task.currency
                  ? costLabel(task.cost, task.currency)
                  : 'Не указана'}
              </dd>
            </div>
            <div>
              <dt>Срок задачи</dt>
              <dd>{task.due_on ? dateLabel(task.due_on) : 'Не указан'}</dd>
            </div>
            <div>
              <dt>Исполнитель</dt>
              <dd>{task.assignee_name ?? 'Не назначен'}</dd>
            </div>
            <div>
              <dt>Подразделения</dt>
              <dd>
                {task.departments.map((department) => department.name).join(', ') || 'Не выбраны'}
              </dd>
            </div>
          </dl>
          <div className="modal-actions">
            <button className="button secondary" onClick={onClose}>
              Закрыть
            </button>
            <button className="button primary" onClick={() => onEdit(task)}>
              <Pencil size={16} />
              Редактировать обучение
            </button>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
