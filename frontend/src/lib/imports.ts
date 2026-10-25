import { request } from './api';

export const entityLabels = {
  departments: 'Отделы',
  employees: 'Сотрудники',
  teams: 'Команды',
  skills: 'Навыки',
};
export type Entity = keyof typeof entityLabels;
export interface ImportIssue {
  entity: string;
  external_id: string;
  message: string;
  line?: number;
  sheet?: string;
}
export interface ImportResult {
  total: number;
  counts: Partial<Record<Entity, { created: number; updated: number; unchanged: number }>>;
  affected_employees?: number;
  records: { entity: Entity; external_id: string; label: string; action: string }[];
  errors?: ImportIssue[];
  error_count?: number;
  fingerprint?: string;
  run_id?: number;
}
export interface IntegrationKey {
  id: number;
  name: string;
  source: string;
  prefix: string;
  entities: Entity[];
  is_active: boolean;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
}
export interface ImportRun {
  id: number;
  source: string;
  request_id: string;
  channel: string;
  status: string;
  actor_username: string;
  created_at: string;
  result: ImportResult;
}
export function fileImport(
  file: File,
  source: string,
  confirmed?: { fingerprint: string; request_id: string },
) {
  const form = new FormData();
  form.append('file', file);
  form.append('source', source);
  if (confirmed) {
    form.append('fingerprint', confirmed.fingerprint);
    form.append('request_id', confirmed.request_id);
  }
  return request<ImportResult>(`/imports/${confirmed ? 'apply' : 'preview'}`, {
    method: 'POST',
    body: form,
  });
}
