import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './lib/auth';
import { LoginPage } from './pages/LoginPage';
import { PasswordPage } from './pages/PasswordPage';
import { AccountsPage } from './pages/AccountsPage';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { DepartmentsPage } from './pages/DepartmentsPage';
import { EmployeeDetailPage } from './pages/EmployeeDetailPage';
import { EmployeesPage } from './pages/EmployeesPage';
import { MatrixPage } from './pages/MatrixPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { SkillsPage } from './pages/SkillsPage';
import { TasksPage } from './pages/TasksPage';
import { TrainingCalendarPage } from './pages/TrainingCalendarPage';
import { TeamsPage } from './pages/TeamsPage';
import { TeamDetailPage } from './pages/TeamDetailPage';
import { ImportsPage } from './pages/ImportsPage';

export function App() {
  const { user, globalAccess } = useAuth();
  if (!user) return <LoginPage />;
  const home = user.employee_id ? `/employees/${user.employee_id}` : '/tasks';
  const fallback = <Navigate to={home} replace />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={globalAccess ? <DashboardPage /> : fallback} />
        <Route path="employees" element={user.role !== 'employee' ? <EmployeesPage /> : fallback} />
        <Route path="employees/:id" element={<EmployeeDetailPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="training-calendar" element={<TrainingCalendarPage />} />
        <Route path="teams" element={<TeamsPage />} />
        <Route path="teams/:id" element={<TeamDetailPage />} />
        <Route path="departments" element={globalAccess ? <DepartmentsPage /> : fallback} />
        <Route path="imports" element={globalAccess ? <ImportsPage /> : fallback} />
        <Route path="skills" element={globalAccess ? <SkillsPage /> : fallback} />
        <Route path="matrix" element={user.role !== 'employee' ? <MatrixPage /> : fallback} />
        <Route path="accounts" element={user.role === 'admin' ? <AccountsPage /> : fallback} />
        <Route path="security" element={<PasswordPage />} />
        <Route path="login" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
