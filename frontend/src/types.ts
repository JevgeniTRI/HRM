export type EmployeeStatus = 'active' | 'probation' | 'leave' | 'inactive';
export interface Department {
  id: number;
  name: string;
  description: string;
}
export interface DepartmentSummary extends Department {
  employee_count: number;
  managers: { id: number; name: string }[];
}
export interface Employee {
  about: string;
  experience: string;
  education: string;
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  position: string;
  department_id: number;
  department: Department;
  status: EmployeeStatus;
  hired_at: string;
}
export type EmployeeWrite = Omit<Employee, 'id' | 'department'>;
export interface Skill {
  id: number;
  name: string;
  category: string;
  description: string;
}
export interface SkillSummary extends Skill {
  employee_count: number;
}
export interface Certificate {
  id: number;
  title: string;
  original_name: string;
  content_type: string;
  size: number;
  created_at: string;
}
export interface Assessment {
  skill: Skill;
  current_level: number | null;
  target_level: number;
  state: 'unassessed' | 'met' | 'gap';
  updated_at: string;
  certificates: Certificate[];
}
export interface EmployeeDetail extends Employee {
  skills: Assessment[];
}
export interface EmployeePage {
  items: Employee[];
  total: number;
  page: number;
  page_size: number;
}
export interface Activity {
  actor_username: string;
  id: number;
  kind: string;
  title: string;
  detail: string;
  employee_id: number | null;
  created_at: string;
}
export interface SkillMetric {
  id: number;
  name: string;
  category: string;
  assigned: number;
  assessed: number;
  at_target: number;
  coverage: number;
  average_level: number | null;
}
export interface Dashboard {
  stats: {
    employees: number;
    active_employees: number;
    probation_employees: number;
    leave_employees: number;
    departments: number;
    skills: number;
    assignments: number;
    assessed: number;
    coverage: number;
    gaps: number;
    unassessed: number;
  };
  departments: DepartmentSummary[];
  skill_metrics: SkillMetric[];
  activities: Activity[];
  recent_employees: Employee[];
}
export interface Matrix {
  skills: Skill[];
  employees: EmployeeDetail[];
  total: number;
  page: number;
  page_size: number;
}
export interface EmployeeFilters {
  q?: string;
  department_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}
