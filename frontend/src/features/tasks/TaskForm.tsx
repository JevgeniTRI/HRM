import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { FormError, Modal } from '../../components/ui';
import { useDepartments, useRefreshData } from '../../lib/queries';
import { taskApi } from './api';
import { taskStatuses, taskStatusLabels } from './format';
import { TaskCostFields } from './TaskCostFields';
import { TaskTrainingFields } from './TaskTrainingFields';
import type { Task, TaskDraft, TaskStatus, TaskWrite } from './types';
import { useAuth } from '../../lib/auth';
import { EmployeePicker } from '../../components/EmployeePicker';

function initialDraft(task: Task | undefined, status: TaskStatus): TaskDraft {
  return {
    title: task?.title ?? '',
    description: task?.description ?? '',
    status: task?.status ?? status,
    isTraining: task ? task.learning_source !== null : true,
    source: task?.learning_source ?? 'internal',
    format: task?.learning_format ?? 'individual',
    participants: String(task?.participant_count ?? 1),
    duration: task?.duration_hours ?? '',
    cost: task?.cost ?? '',
    currency: task?.currency ?? 'EUR',
    dueOn: task?.due_on ?? '',
    departmentIds: task?.departments.map((dept) => dept.id) ?? [],
  };
}

function writeValues(draft: TaskDraft): TaskWrite {
  return {
    assignee_id: null,
    title: draft.title.trim(),
    description: draft.description.trim(),
    status: draft.status,
    learning_source: draft.isTraining ? draft.source : null,
    learning_format: draft.isTraining ? draft.format : null,
    participant_count: draft.isTraining ? Number(draft.participants) : null,
    duration_hours: draft.isTraining && draft.duration !== '' ? draft.duration : null,
    cost: draft.cost !== '' ? draft.cost : null,
    currency: draft.cost !== '' ? draft.currency : null,
    due_on: draft.dueOn || null,
    department_ids: draft.departmentIds,
  };
}

export function TaskForm({
  task,
  status = 'todo',
  onClose,
}: {
  task?: Task;
  status?: TaskStatus;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const [draft, setDraft] = useState(() => ({
    ...initialDraft(task, status),
    ...(!task && user?.role === 'manager' ? { departmentIds: [user.department_id!] } : {}),
  }));
  const [assignee, setAssignee] = useState<number | null>(
    task?.assignee_id ?? (user?.role === 'employee' ? user.employee_id : null),
  );
  const departments = useDepartments();
  const refresh = useRefreshData();
  function change(patch: Partial<TaskDraft>) {
    setDraft((previous) => ({ ...previous, ...patch }));
  }
  const save = useMutation({
    mutationFn: () => taskApi.save({ ...writeValues(draft), assignee_id: assignee }, task),
    onSuccess: async () => {
      await refresh();
      onClose();
    },
    onError: () => refresh(),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!save.isPending) save.mutate();
  }
  function toggleDepartment(id: number) {
    change({
      departmentIds: draft.departmentIds.includes(id)
        ? draft.departmentIds.filter((value) => value !== id)
        : [...draft.departmentIds, id],
    });
  }
  return (
    <Modal
      title={task ? 'Редактировать задачу' : 'Новая задача'}
      subtitle="Планируйте работу и обучение, учитывайте стоимость и время команды."
      onClose={() => {
        if (!save.isPending) onClose();
      }}
      wide
    >
      <form className="modal-form task-form" onSubmit={submit}>
        <fieldset className="task-form-controls" disabled={save.isPending}>
          <label>
            Название
            <input
              aria-label="Название задачи"
              autoFocus
              required
              maxLength={160}
              value={draft.title}
              onChange={(event) => change({ title: event.target.value })}
              placeholder="Например, Практикум по Python"
            />
          </label>
          <label>
            Описание
            <textarea
              aria-label="Описание задачи"
              rows={3}
              maxLength={5000}
              value={draft.description}
              onChange={(event) => change({ description: event.target.value })}
              placeholder="Цель, содержание и ожидаемый результат…"
            />
          </label>
          <div className="form-grid">
            <label>
              Статус
              <select
                aria-label="Статус в карточке"
                value={draft.status}
                onChange={(event) => change({ status: event.target.value as TaskStatus })}
              >
                {taskStatuses.map((value) => (
                  <option key={value} value={value}>
                    {taskStatusLabels[value]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Срок
              <input
                aria-label="Срок задачи"
                type="date"
                value={draft.dueOn}
                onChange={(event) => change({ dueOn: event.target.value })}
              />
            </label>
          </div>
          <label className="task-training-toggle">
            <input
              type="checkbox"
              checked={draft.isTraining}
              onChange={(event) => change({ isTraining: event.target.checked })}
            />
            <span>
              <strong>Это обучение</strong>
              <small>Добавить источник, формат, участников и человекочасы</small>
            </span>
          </label>
          {draft.isTraining && <TaskTrainingFields draft={draft} change={change} />}
          {user?.role !== 'employee' && (
            <EmployeePicker value={assignee} onChange={setAssignee} label="Исполнитель" />
          )}
          <fieldset className="task-form-section" disabled={user?.role === 'employee' && !!task}>
            <legend>Задействованные подразделения</legend>
            {departments.isPending ? (
              <p className="task-form-hint">Загружаем подразделения…</p>
            ) : departments.isError ? (
              <>
                <FormError error={departments.error} />
                <button
                  type="button"
                  className="button secondary compact"
                  onClick={() => departments.refetch()}
                >
                  Повторить
                </button>
              </>
            ) : (
              <div className="department-choices">
                {departments.data.map((dept) => (
                  <label
                    key={dept.id}
                    className={draft.departmentIds.includes(dept.id) ? 'selected' : ''}
                  >
                    <input
                      type="checkbox"
                      checked={draft.departmentIds.includes(dept.id)}
                      onChange={() => toggleDepartment(dept.id)}
                    />
                    {dept.name}
                  </label>
                ))}
              </div>
            )}
            <p className="task-form-hint">
              {user?.role === 'manager'
                ? 'Назначьте задачу сотруднику своего отдела или всему отделу.'
                : 'Выберите подразделения, которые участвуют в задаче.'}
            </p>
          </fieldset>
          <TaskCostFields draft={draft} change={change} />
        </fieldset>
        <FormError error={save.error} />
        <div className="modal-actions">
          <button
            type="button"
            className="button secondary"
            disabled={save.isPending}
            onClick={onClose}
          >
            Отмена
          </button>
          <button
            className="button primary"
            disabled={save.isPending || departments.isPending || departments.isError}
          >
            {save.isPending ? 'Сохраняем…' : task ? 'Сохранить задачу' : 'Создать задачу'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
