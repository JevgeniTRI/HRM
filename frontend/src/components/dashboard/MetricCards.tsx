import { ArrowUpRight, BookOpen, Building2, Target, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Dashboard } from '../../types';

export function MetricCards({ stats }: { stats: Dashboard['stats'] }) {
  const metrics = [
    {
      label: 'СОТРУДНИКОВ',
      value: stats.employees,
      detail: `${stats.active_employees} работают · ${stats.probation_employees} на испытательном`,
      icon: Users,
      color: 'lilac',
      href: '/employees',
    },
    {
      label: 'ПОДРАЗДЕЛЕНИЙ',
      value: stats.departments,
      detail: 'Команды вашего пространства',
      icon: Building2,
      color: 'blue',
      href: '/departments',
    },
    {
      label: 'НАВЫКОВ В КАТАЛОГЕ',
      value: stats.skills,
      detail: `${stats.assignments} назначений сотрудникам`,
      icon: BookOpen,
      color: 'peach',
      href: '/skills',
    },
    {
      label: 'ДОСТИГЛИ ЦЕЛИ',
      value: `${stats.coverage}%`,
      detail: `${stats.gaps} ниже цели · ${stats.unassessed} без оценки`,
      icon: Target,
      color: 'green',
      href: '/matrix',
    },
  ];
  return (
    <div className="metrics-grid">
      {metrics.map(({ label, value, detail, icon: Icon, color, href }) => (
        <Link to={href} key={label} className="metric-card">
          <div className="metric-top">
            <span>{label}</span>
            <span className={`metric-icon ${color}`}>
              <Icon size={19} strokeWidth={1.8} />
            </span>
          </div>
          <div className="metric-value">
            {value}
            <ArrowUpRight size={16} />
          </div>
          <p>{detail}</p>
        </Link>
      ))}
    </div>
  );
}
