import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Employee } from '../../types';
import { dateLabel, fullName } from '../../lib/format';
import { Avatar, Empty, StatusBadge } from '../ui';

export function RecentEmployees({ employees }: { employees: Employee[] }) {
  return (
    <section className="card recent-card">
      <div className="card-heading">
        <div>
          <h2>Новые лица в команде</h2>
          <p>Последние добавленные сотрудники</p>
        </div>
        <Link to="/employees" className="text-link">
          Все сотрудники
          <ArrowRight size={15} />
        </Link>
      </div>
      {!employees.length ? (
        <Empty
          title="Познакомимся с командой?"
          description="Добавьте первого сотрудника, чтобы начать."
        />
      ) : (
        <div className="recent-employees">
          {employees.map((employee) => (
            <Link className="recent-person" key={employee.id} to={`/employees/${employee.id}`}>
              <Avatar employee={employee} />
              <div>
                <strong>{fullName(employee)}</strong>
                <p>{employee.position}</p>
                <span>{employee.department.name}</span>
              </div>
              <div className="recent-meta">
                <StatusBadge status={employee.status} />
                <small>С {dateLabel(employee.hired_at)}</small>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
