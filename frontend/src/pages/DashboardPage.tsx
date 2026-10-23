import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowDownToLine, Plus, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { ErrorState, Loading, PageHeader } from '../components/ui';
import { EmployeeForm } from '../components/EmployeeForm';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { DepartmentDistribution } from '../components/dashboard/DepartmentDistribution';
import { MetricCards } from '../components/dashboard/MetricCards';
import { RecentEmployees } from '../components/dashboard/RecentEmployees';
import { SkillOverview } from '../components/dashboard/SkillOverview';

export function DashboardPage() {
  const dashboard = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard });
  const [create, setCreate] = useState(false);
  const navigate = useNavigate();
  const today = new Intl.DateTimeFormat('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(new Date());
  if (dashboard.isPending) return <Loading />;
  if (dashboard.isError)
    return <ErrorState error={dashboard.error} retry={() => dashboard.refetch()} />;
  const { stats, departments, activities, skill_metrics, recent_employees } = dashboard.data;
  return (
    <>
      <PageHeader
        eyebrow="ОБЗОР КОМАНДЫ"
        title="Главная"
        description="Люди, навыки и развитие — в одном пространстве."
      >
        <a className="button secondary" href="/api/employees/export">
          <ArrowDownToLine size={16} />
          Экспорт
        </a>
        <button className="button primary" onClick={() => setCreate(true)}>
          <Plus size={18} />
          Добавить сотрудника
        </button>
      </PageHeader>
      <div className="dashboard-welcome">
        <div>
          <span className="welcome-icon">
            <Sparkles size={19} />
          </span>
          <span>
            <strong>Хороший день для развития команды</strong>
            <small>Каждый новый навык — шаг к большим возможностям.</small>
          </span>
        </div>
        <time className="today-label">{today}</time>
      </div>
      <MetricCards stats={stats} />
      <div className="dashboard-middle">
        <DepartmentDistribution departments={departments} employees={stats.employees} />
        <ActivityFeed activities={activities} />
      </div>
      <SkillOverview metrics={skill_metrics} />
      <RecentEmployees employees={recent_employees} />
      {create && (
        <EmployeeForm
          onClose={() => setCreate(false)}
          onSaved={(id) => navigate(`/employees/${id}`)}
        />
      )}
    </>
  );
}
