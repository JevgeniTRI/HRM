import { useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { ArrowDownToLine, ArrowUpRight, Plus, Users } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { api, queryString } from '../lib/api';
import { useAuth } from '../lib/auth';
import { dateLabel, fullName } from '../lib/format';
import { useEmployeeFilters } from '../lib/useEmployeeFilters';
import {
  Avatar,
  Empty,
  ErrorState,
  Loading,
  PageHeader,
  Pagination,
  StatusBadge,
} from '../components/ui';
import { EmployeeFilters } from '../components/EmployeeFilters';
import { EmployeeForm } from '../components/EmployeeForm';

export function EmployeesPage() {
  const { globalAccess } = useAuth();
  const [filters, setPage] = useEmployeeFilters(10);
  const employees = useQuery({
    queryKey: ['employees', filters],
    queryFn: () => api.employees(filters),
    placeholderData: keepPreviousData,
  });
  const [create, setCreate] = useState(false);
  const navigate = useNavigate();
  return (
    <>
      <PageHeader
        eyebrow="ЛЮДИ И КОМАНДЫ"
        title={globalAccess ? 'Сотрудники' : 'Мой отдел'}
        description={
          globalAccess
            ? 'Вся команда, роли и контактные данные.'
            : 'Сотрудники вашего отдела и их карточки.'
        }
      >
        <a
          className="button secondary"
          href={`/api/employees/export?${queryString({ ...filters, page: undefined, page_size: undefined })}`}
        >
          <ArrowDownToLine size={16} />
          Экспорт CSV
        </a>
        {globalAccess && (
          <button className="button primary" onClick={() => setCreate(true)}>
            <Plus size={18} />
            Добавить сотрудника
          </button>
        )}
      </PageHeader>
      <section className="card list-card">
        <div className="list-title">
          <h2>
            <Users size={19} />
            Ваша команда<span className="count-tag">{employees.data?.total ?? '—'}</span>
          </h2>
          <span>Каждый человек имеет значение</span>
        </div>
        <EmployeeFilters />
        {employees.isPending ? (
          <Loading />
        ) : employees.isError ? (
          <ErrorState error={employees.error} retry={() => employees.refetch()} />
        ) : !employees.data.items.length ? (
          <Empty
            title="Сотрудники не найдены"
            description="Измените фильтры или добавьте первого сотрудника."
          >
            {globalAccess && (
              <button className="button primary" onClick={() => setCreate(true)}>
                <Plus size={16} />
                Добавить сотрудника
              </button>
            )}
          </Empty>
        ) : (
          <div className={`table-scroll ${employees.isFetching ? 'is-fetching' : ''}`}>
            <table className="employees-table">
              <thead>
                <tr>
                  <th>Сотрудник</th>
                  <th>Должность</th>
                  <th>Подразделение</th>
                  <th>Статус</th>
                  <th>Дата приёма</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {employees.data.items.map((employee) => (
                  <tr key={employee.id}>
                    <td>
                      <Link to={`/employees/${employee.id}`} className="person-cell">
                        <Avatar employee={employee} />
                        <div>
                          <strong>{fullName(employee)}</strong>
                          <small>{employee.email}</small>
                        </div>
                      </Link>
                    </td>
                    <td>{employee.position}</td>
                    <td>
                      <span className="department-tag">{employee.department.name}</span>
                    </td>
                    <td>
                      <StatusBadge status={employee.status} />
                    </td>
                    <td className="nowrap">{dateLabel(employee.hired_at)}</td>
                    <td>
                      <Link
                        className="icon-link"
                        to={`/employees/${employee.id}`}
                        aria-label={`Открыть карточку: ${fullName(employee)}`}
                      >
                        <ArrowUpRight size={18} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {employees.data && (
          <Pagination
            page={filters.page ?? 1}
            total={employees.data.total}
            pageSize={10}
            onChange={setPage}
          />
        )}
      </section>
      {create && (
        <EmployeeForm
          onClose={() => setCreate(false)}
          onSaved={(id) => navigate(`/employees/${id}`)}
        />
      )}
    </>
  );
}
