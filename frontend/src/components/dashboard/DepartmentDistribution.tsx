import { ArrowRight, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { DepartmentSummary } from '../../types';
import { Empty } from '../ui';

export function DepartmentDistribution({
  departments,
  employees,
}: {
  departments: DepartmentSummary[];
  employees: number;
}) {
  return (
    <section className="card departments-card">
      <div className="card-heading">
        <div>
          <h2>Структура команды</h2>
          <p>Сотрудники по подразделениям</p>
        </div>
        <Link to="/departments" className="icon-link" aria-label="Все подразделения">
          <ArrowUpRight size={19} />
        </Link>
      </div>
      {!departments.length ? (
        <Empty title="Пока нет подразделений" description="Создайте структуру вашей команды." />
      ) : (
        <>
          <div className="team-total">
            <strong>{employees}</strong>
            <span>
              сотрудников
              <br />в {departments.length} подразделениях
            </span>
          </div>
          <div className="department-bars">
            {departments.map((dept, index) => (
              <Link
                to={`/employees?department_id=${dept.id}`}
                className="department-row"
                key={dept.id}
              >
                <div>
                  <span>
                    <i className={`department-dot color-${index % 4}`} />
                    {dept.name}
                  </span>
                  <strong>{dept.employee_count}</strong>
                </div>
                <div className="bar-track">
                  <span
                    className={`color-${index % 4}`}
                    style={{ width: `${employees ? (dept.employee_count / employees) * 100 : 0}%` }}
                  />
                </div>
              </Link>
            ))}
          </div>
          <Link to="/departments" className="card-bottom-link">
            Все подразделения
            <ArrowRight size={15} />
          </Link>
        </>
      )}
    </section>
  );
}
