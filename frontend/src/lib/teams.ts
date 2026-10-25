import { request, queryString } from './api';
import type { Department, EmployeeReference, EmployeePage } from '../types';

export interface Team {
  id: number;
  code: string;
  name: string;
  department: Department;
  manager: EmployeeReference | null;
  supervisor: EmployeeReference | null;
  member_count: number;
  version: number;
}
export interface ImportPreview {
  total: number;
  create_count: number;
  assign_count: number;
  unchanged_count: number;
  error_count: number;
  fingerprint: string;
  rows: {
    line: number;
    email: string;
    name: string;
    team_code: string;
    action: 'create' | 'assign' | 'unchanged';
  }[];
  errors: { line: number; message: string }[];
}
export type ImportResult = Pick<
  ImportPreview,
  'total' | 'create_count' | 'assign_count' | 'unchanged_count'
>;
const json = (data: unknown) => JSON.stringify(data);
export const teamsApi = {
  list: (filters: { department_id?: string; q?: string }) =>
    request<Team[]>(`/teams?${queryString(filters)}`),
  read: (id: number) => request<Team>(`/teams/${id}`),
  create: (data: {
    code: string;
    name: string;
    department_id: number;
    manager_id: number | null;
    supervisor_id: number | null;
  }) => request<Team>('/teams', { method: 'POST', body: json(data) }),
  members: (id: number, page: number) => request<EmployeePage>(`/teams/${id}/members?page=${page}`),
  candidates: (id: number, q: string, unassigned: boolean, page = 1) =>
    request<EmployeePage>(
      `/teams/${id}/candidates?${queryString({ q, unassigned_only: unassigned, page })}`,
    ),
  assign: (team: Team, employee_ids: number[]) =>
    request<Team>(`/teams/${team.id}/members`, {
      method: 'POST',
      body: json({ employee_ids, version: team.version }),
    }),
  replace: (team: Team, manager_id: number) =>
    request<Team>(`/teams/${team.id}/manager`, {
      method: 'PUT',
      body: json({ manager_id, version: team.version }),
    }),
  remove: (team: Team, id: number) =>
    request<void>(`/teams/${team.id}/members/${id}?version=${team.version}`, { method: 'DELETE' }),
  delete: (team: Team) =>
    request<void>(`/teams/${team.id}?version=${team.version}`, { method: 'DELETE' }),
  preview: (file: File) => {
    const data = new FormData();
    data.append('file', file);
    return request<ImportPreview>('/teams/import/preview', { method: 'POST', body: data });
  },
  import: (file: File, fingerprint: string) => {
    const data = new FormData();
    data.append('file', file);
    data.append('fingerprint', fingerprint);
    return request<ImportResult>('/teams/import', { method: 'POST', body: data });
  },
};
