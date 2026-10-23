import { queryString, request } from '../../lib/api';
import type { Task, TaskFilters, TaskPage, TaskStatus, TaskSummary, TaskWrite } from './types';

export const taskApi = {
  list: (filters: TaskFilters, status: TaskStatus, page: number) =>
    request<TaskPage>(`/tasks?${queryString({ ...filters, status, page, page_size: 20 })}`),
  summary: (filters: TaskFilters) => request<TaskSummary>(`/tasks/summary?${queryString(filters)}`),
  read: (id: number) => request<Task>(`/tasks/${id}`),
  save: (data: TaskWrite, task?: Task) =>
    request<Task>(`/tasks${task ? `/${task.id}` : ''}`, {
      method: task ? 'PUT' : 'POST',
      body: JSON.stringify({ ...data, ...(task ? { version: task.version } : {}) }),
    }),
  move: (task: Task, status: TaskStatus) =>
    request<Task>(`/tasks/${task.id}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status, version: task.version }),
    }),
  delete: (task: Task) =>
    request<void>(`/tasks/${task.id}?version=${task.version}`, { method: 'DELETE' }),
  estimate: (duration_hours: string, participant_count: number) =>
    request<{ person_hours: string }>('/tasks/estimate', {
      method: 'POST',
      body: JSON.stringify({ duration_hours, participant_count }),
    }),
};
