import type { Department } from '../../types';

export type TaskStatus = 'todo' | 'in_progress' | 'done';
export type LearningSource = 'internal' | 'external';
export type LearningFormat = 'individual' | 'group';
export type Currency = 'EUR' | 'USD' | 'UAH' | 'GBP';

export interface TaskWrite {
  assignee_id: number | null;
  title: string;
  description: string;
  status: TaskStatus;
  learning_source: LearningSource | null;
  learning_format: LearningFormat | null;
  participant_count: number | null;
  duration_hours: string | null;
  cost: string | null;
  currency: Currency | null;
  due_on: string | null;
  start_on: string | null;
  end_on: string | null;
  department_ids: number[];
}
export interface Task extends Omit<TaskWrite, 'department_ids'> {
  assignee_name: string | null;
  id: number;
  departments: Department[];
  person_hours: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}
export interface TaskPage {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
}
export interface TaskFilters {
  q?: string;
  department_id?: string;
  learning_source?: string;
  learning_format?: string;
  is_training?: string;
}
export interface TaskSummary {
  total: number;
  status_counts: Record<TaskStatus, number>;
  person_hours: string;
  training_count: number;
  unestimated_training_count: number;
  without_cost_count: number;
  costs: { currency: Currency; amount: string }[];
}
export interface PendingMove {
  task: Task;
  status: TaskStatus;
}
export interface TaskDraft {
  title: string;
  description: string;
  status: TaskStatus;
  isTraining: boolean;
  source: LearningSource;
  format: LearningFormat;
  participants: string;
  duration: string;
  cost: string;
  currency: Currency;
  dueOn: string;
  startOn: string;
  endOn: string;
  departmentIds: number[];
}
