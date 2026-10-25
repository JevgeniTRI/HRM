import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Network, Pencil } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { EmployeeDetail, EmployeeReference, OrganizationRole } from '../types';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { fullName } from '../lib/format';
import { useRefreshData } from '../lib/queries';
import { useDebouncedValue } from '../lib/useDebouncedValue';
import { EmployeePicker } from './EmployeePicker';
import { FormError, Modal } from './ui';

const organizationLabels: Record<OrganizationRole, string> = {
  head: 'Руководитель отдела',
  intermediate: 'Промежуточный руководитель',
  employee: 'Сотрудник',
};

function ReportsPicker({
  employee,
  selected,
  onChange,
}: {
  employee: EmployeeDetail;
  selected: EmployeeReference[];
  onChange: (people: EmployeeReference[]) => void;
}) {
  const [search, setSearch] = useState('');
  const q = useDebouncedValue(search);
  const people = useQuery({
    queryKey: ['organization-candidates', employee.department_id, q],
    queryFn: () =>
      api.employees({ department_id: String(employee.department_id), q, page_size: 100 }),
  });
  const fixed = new Set(employee.direct_reports.map((person) => person.id));
  return (
    <div className="organization-report-picker">
      <h3>
        Прямые подчинённые <span className="count-tag">{selected.length}</span>
      </h3>
      {!!selected.length && (
        <ul className="organization-selected">
          {selected.map((person) => (
            <li key={person.id}>{fullName(person)}</li>
          ))}
        </ul>
      )}
      <label>
        Поиск подчинённых в отделе
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          maxLength={100}
          placeholder="Имя, фамилия или email"
        />
      </label>
      <div className="organization-candidates" role="group" aria-label="Прямые подчинённые">
        {people.isPending ? (
          <p className="muted">Загружаем сотрудников…</p>
        ) : (
          people.data?.items
            .filter((person) => person.id !== employee.id && person.id !== employee.manager_id)
            .map((person) => {
              const checked = selected.some((item) => item.id === person.id);
              return (
                <label className="organization-checkbox" key={person.id}>
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={fixed.has(person.id)}
                    onChange={() =>
                      onChange(
                        checked
                          ? selected.filter((item) => item.id !== person.id)
                          : [...selected, person],
                      )
                    }
                  />
                  <span>
                    {fullName(person)}
                    <small>
                      {person.position}
                      {fixed.has(person.id) ? ' · Уже в подчинении' : ''}
                    </small>
                  </span>
                </label>
              );
            })
        )}
      </div>
      {(people.data?.total ?? 0) > 100 && (
        <p className="field-hint">Уточните поиск: показаны первые 100 сотрудников отдела.</p>
      )}
      <p className="field-hint">
        Чтобы убрать текущего подчинённого, назначьте ему другого руководителя в его карточке.
      </p>
      <FormError error={people.error} />
    </div>
  );
}

function OrganizationForm({
  employee,
  onClose,
}: {
  employee: EmployeeDetail;
  onClose: () => void;
}) {
  const [kind, setKind] = useState<OrganizationRole>(employee.organization_role);
  const [managerId, setManagerId] = useState(employee.manager_id);
  const [reports, setReports] = useState(employee.direct_reports);
  const refresh = useRefreshData();
  const save = useMutation({
    mutationFn: () =>
      api.saveOrganization(employee.id, {
        kind,
        manager_id: kind === 'head' ? null : managerId,
        report_ids: reports.map((person) => person.id),
      }),
    onSuccess: async () => {
      await refresh();
      onClose();
    },
  });
  return (
    <Modal
      title="Настроить подчинённость"
      subtitle={`${fullName(employee)} · ${employee.department.name}`}
      onClose={() => {
        if (!save.isPending) onClose();
      }}
    >
      <form
        className="modal-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!save.isPending) save.mutate();
        }}
      >
        <fieldset className="organization-fields" disabled={save.isPending}>
          <label>
            Роль в отделе
            <select
              value={kind}
              onChange={(event) => {
                setKind(event.target.value as OrganizationRole);
                setReports(employee.direct_reports);
              }}
            >
              <option value="head">Руководитель отдела</option>
              <option value="intermediate">Промежуточный руководитель</option>
              <option value="employee" disabled={employee.direct_reports.length > 0}>
                Подчинённый (сотрудник)
              </option>
            </select>
          </label>
          <p className="field-hint">
            Руководитель видит свою ветку подчинения только в отделе «{employee.department.name}».
          </p>
          {kind !== 'head' && (
            <EmployeePicker
              label="Непосредственный руководитель"
              value={managerId}
              onChange={setManagerId}
              departmentId={employee.department_id}
              excludeId={employee.id}
              required
              emptyLabel="Выберите руководителя в отделе"
            />
          )}
          {kind !== 'employee' && (
            <ReportsPicker employee={employee} selected={reports} onChange={setReports} />
          )}
          <p className="field-hint">
            Без подчинённых пользователь считается сотрудником. С подчинёнными и своим начальником —
            промежуточным руководителем; без начальника — руководителем отдела. Первый назначенный
            подчинённый автоматически делает пользователя руководителем.
          </p>
          <p className="field-hint">
            При смене роли сотруднику потребуется войти заново. Права администратора и power_user
            сохраняются.
          </p>
        </fieldset>
        <FormError error={save.error} />
        <div className="modal-actions">
          <button
            type="button"
            className="button secondary"
            disabled={save.isPending}
            onClick={onClose}
          >
            Отмена
          </button>
          <button className="button primary" disabled={save.isPending}>
            {save.isPending ? 'Сохраняем…' : 'Сохранить подчинённость'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function OrganizationSection({ employee }: { employee: EmployeeDetail }) {
  const { globalAccess } = useAuth();
  const [edit, setEdit] = useState(false);
  return (
    <section className="card organization-card" aria-label="Руководитель и подчинённые">
      <div className="card-heading">
        <div>
          <h2>
            <Network size={19} /> Руководитель и подчинённые
          </h2>
          <p>
            {organizationLabels[employee.organization_role]} · {employee.department.name}
          </p>
        </div>
        {globalAccess && (
          <button className="button secondary compact" onClick={() => setEdit(true)}>
            <Pencil size={15} />
            Настроить подчинённость
          </button>
        )}
      </div>
      <div className="organization-body">
        {employee.team && (
          <p>
            Команда: <Link to={`/teams/${employee.team.id}`}>{employee.team.name}</Link> ·{' '}
            {employee.team.code}
          </p>
        )}
        <h3>Непосредственный руководитель</h3>
        {employee.manager ? (
          <div className="organization-person">
            <strong>
              {globalAccess ? (
                <Link to={`/employees/${employee.manager.id}`}>{fullName(employee.manager)}</Link>
              ) : (
                fullName(employee.manager)
              )}
            </strong>
            <span>
              {employee.manager.position} · {employee.manager.department.name}
            </span>
          </div>
        ) : (
          <p className="muted">
            {employee.is_manager ? 'Нет — руководитель отдела' : 'Пока не назначен'}
          </p>
        )}
        {employee.is_manager && (
          <>
            <h3>
              Прямые подчинённые <span className="count-tag">{employee.direct_reports.length}</span>
            </h3>
            <ul className="organization-reports">
              {employee.direct_reports.map((person) => (
                <li key={person.id} className="organization-person">
                  <strong>
                    <Link to={`/employees/${person.id}`}>{fullName(person)}</Link>
                    {person.is_manager && (
                      <span className="count-tag">
                        {organizationLabels[person.organization_role]}
                      </span>
                    )}
                  </strong>
                  <span>
                    {person.position} · {person.department.name}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
      {edit && <OrganizationForm employee={employee} onClose={() => setEdit(false)} />}
    </section>
  );
}
