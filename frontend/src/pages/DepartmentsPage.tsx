import { useState } from 'react';
import { ArrowRight, Building2, Pencil, Plus, Trash2, UserRound, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Department } from '../types';
import { api } from '../lib/api';
import { useDepartments } from '../lib/queries';
import { CatalogForm, DeleteDialog } from '../components/CatalogForm';
import { Empty, ErrorState, Loading, PageHeader } from '../components/ui';

export function DepartmentsPage() {
  const departments = useDepartments();
  const [edit, setEdit] = useState<Department | 'new' | null>(null);
  const [remove, setRemove] = useState<Department | null>(null);
  return (
    <>
      <PageHeader
        eyebrow="СТРУКТУРА ОРГАНИЗАЦИИ"
        title="Подразделения"
        description="Команды, которые вместе создают результат."
      >
        <button className="button primary" onClick={() => setEdit('new')}>
          <Plus size={18} />
          Добавить подразделение
        </button>
      </PageHeader>
      {departments.isPending ? (
        <Loading />
      ) : departments.isError ? (
        <ErrorState error={departments.error} retry={() => departments.refetch()} />
      ) : !departments.data.length ? (
        <section className="card">
          <Empty
            title="Создайте первое подразделение"
            description="Подразделения помогут организовать сотрудников и их компетенции."
          >
            <button className="button primary" onClick={() => setEdit('new')}>
              <Plus size={16} />
              Добавить подразделение
            </button>
          </Empty>
        </section>
      ) : (
        <div className="catalog-grid department-grid">
          {departments.data.map((department, index) => (
            <article className="card catalog-card department-catalog" key={department.id}>
              <div className="catalog-card-top">
                <span className={`catalog-icon ${['lilac', 'blue', 'peach', 'green'][index % 4]}`}>
                  <Building2 size={23} strokeWidth={1.6} />
                </span>
                <div>
                  <button
                    className="icon-button"
                    aria-label={`Редактировать ${department.name}`}
                    onClick={() => setEdit(department)}
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    className="icon-button"
                    aria-label={`Удалить ${department.name}`}
                    onClick={() => setRemove(department)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <h2>{department.name}</h2>
              <div className="department-card-manager">
                <UserRound size={16} aria-hidden="true" />
                <span>
                  {department.managers.length ? (
                    <>
                      {department.managers.length > 1
                        ? 'Руководители отдела: '
                        : 'Руководитель отдела: '}
                      {department.managers.map((manager, managerIndex) => (
                        <span key={manager.id}>
                          {managerIndex > 0 && ', '}
                          <Link to={`/employees/${manager.id}`}>{manager.name}</Link>
                        </span>
                      ))}
                    </>
                  ) : (
                    'Руководитель не назначен'
                  )}
                </span>
              </div>
              <p>{department.description || 'Описание ещё не добавлено.'}</p>
              <div className="department-card-count">
                <Users size={19} />
                <strong>{department.employee_count}</strong>
                <span>сотрудников</span>
              </div>
              <Link
                to={`/employees?department_id=${department.id}`}
                className="catalog-card-footer department-card-link"
              >
                Посмотреть команду
                <ArrowRight size={16} />
              </Link>
            </article>
          ))}
        </div>
      )}
      {edit && (
        <CatalogForm
          title={edit === 'new' ? 'Новое подразделение' : 'Редактировать подразделение'}
          initial={edit === 'new' ? undefined : edit}
          onSave={({ name, description }) =>
            api.saveDepartment({ name, description }, edit === 'new' ? undefined : edit.id)
          }
          onClose={() => setEdit(null)}
        />
      )}
      {remove && (
        <DeleteDialog
          title="Удалить подразделение?"
          description={`Подразделение «${remove.name}» можно удалить, когда к нему не привязаны сотрудники или задачи. Переведите сотрудников и измените подразделения в карточках задач.`}
          onDelete={() => api.deleteDepartment(remove.id)}
          onClose={() => setRemove(null)}
        />
      )}
    </>
  );
}
