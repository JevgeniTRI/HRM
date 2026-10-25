import type {
  Assessment,
  Certificate,
  Dashboard,
  Department,
  DepartmentSummary,
  EmployeeDetail,
  EmployeeFilters,
  EmployeePage,
  EmployeeWrite,
  Matrix,
  OrganizationRole,
  Skill,
  SkillSummary,
} from '../types';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      credentials: 'same-origin',
      headers: {
        'X-HRM-Request': '1',
        ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError('Не удалось подключиться к серверу. Проверьте соединение.', 0);
  }
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login' && path !== '/auth/me') {
      window.dispatchEvent(new Event('hrm-session-expired'));
    }
    const body = await response.json().catch(() => ({}));
    const message =
      typeof body.detail === 'string'
        ? body.detail
        : response.status === 422
          ? 'Проверьте заполнение полей и допустимые значения.'
          : 'Не удалось выполнить запрос. Попробуйте ещё раз.';
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export function queryString(filters: object): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value));
  });
  return params.toString();
}

const body = (data: unknown) => JSON.stringify(data);
export const api = {
  dashboard: () => request<Dashboard>('/dashboard'),
  departments: () => request<DepartmentSummary[]>('/departments'),
  saveDepartment: (data: Omit<Department, 'id'>, id?: number) =>
    request<Department>(`/departments${id ? `/${id}` : ''}`, {
      method: id ? 'PUT' : 'POST',
      body: body(data),
    }),
  deleteDepartment: (id: number) => request<void>(`/departments/${id}`, { method: 'DELETE' }),
  employees: (filters: EmployeeFilters) =>
    request<EmployeePage>(`/employees?${queryString(filters)}`),
  employee: (id: number) => request<EmployeeDetail>(`/employees/${id}`),
  saveOrganization: (
    id: number,
    data: { kind: OrganizationRole; manager_id: number | null; report_ids: number[] },
  ) =>
    request<EmployeeDetail>(`/employees/${id}/organization`, {
      method: 'PUT',
      body: body(data),
    }),
  saveEmployee: (data: EmployeeWrite, id?: number) =>
    request<EmployeeDetail>(`/employees${id ? `/${id}` : ''}`, {
      method: id ? 'PUT' : 'POST',
      body: body(data),
    }),
  deleteEmployee: (id: number) => request<void>(`/employees/${id}`, { method: 'DELETE' }),
  uploadEmployeePhoto: (id: number, file: File) => {
    const data = new FormData();
    data.append('file', file);
    return request<void>(`/employees/${id}/photo`, { method: 'POST', body: data });
  },
  deleteEmployeePhoto: (id: number) =>
    request<void>(`/employees/${id}/photo`, { method: 'DELETE' }),
  employeePhotoUrl: (id: number, version: number) => `/api/employees/${id}/photo?v=${version}`,
  skills: () => request<SkillSummary[]>('/skills'),
  saveSkill: (data: Omit<Skill, 'id'>, id?: number) =>
    request<Skill>(`/skills${id ? `/${id}` : ''}`, {
      method: id ? 'PUT' : 'POST',
      body: body(data),
    }),
  deleteSkill: (id: number) => request<void>(`/skills/${id}`, { method: 'DELETE' }),
  assess: (
    employeeId: number,
    skillId: number,
    current_level: number | null,
    target_level: number,
  ) =>
    request<Assessment>(`/employees/${employeeId}/skills/${skillId}`, {
      method: 'PUT',
      body: body({ current_level, target_level }),
    }),
  removeAssessment: (employeeId: number, skillId: number) =>
    request<void>(`/employees/${employeeId}/skills/${skillId}`, { method: 'DELETE' }),
  uploadCertificate: (employeeId: number, skillId: number, file: File, title: string) => {
    const data = new FormData();
    data.append('file', file);
    data.append('title', title);
    return request<Certificate>(`/employees/${employeeId}/skills/${skillId}/certificates`, {
      method: 'POST',
      body: data,
    });
  },
  deleteCertificate: (employeeId: number, skillId: number, certificateId: number) =>
    request<void>(`/employees/${employeeId}/skills/${skillId}/certificates/${certificateId}`, {
      method: 'DELETE',
    }),
  certificateUrl: (employeeId: number, skillId: number, certificateId: number, download = false) =>
    `/api/employees/${employeeId}/skills/${skillId}/certificates/${certificateId}/file${download ? '?download=true' : ''}`,
  matrix: (filters: EmployeeFilters) => request<Matrix>(`/matrix?${queryString(filters)}`),
};
