import { Search, SlidersHorizontal } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useDepartments } from '../lib/queries';
import { statusLabels } from '../lib/format';

export function EmployeeFilters() {
  const [params, setParams] = useSearchParams();
  const departments = useDepartments();
  function change(key: string, value: string) {
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        next.delete('page');
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );
  }
  return (
    <div className="filter-toolbar">
      <div className="filter-search">
        <Search size={17} />
        <input
          placeholder="Имя, должность или email…"
          aria-label="Поиск сотрудников"
          maxLength={100}
          value={params.get('q') ?? ''}
          onChange={(event) => change('q', event.target.value)}
        />
      </div>
      <div className="filter-selects">
        <SlidersHorizontal size={17} />
        <select
          aria-label="Подразделение"
          value={params.get('department_id') ?? ''}
          onChange={(event) => change('department_id', event.target.value)}
        >
          <option value="">Все подразделения</option>
          {departments.data?.map((dept) => (
            <option key={dept.id} value={dept.id}>
              {dept.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Статус сотрудника"
          value={params.get('status') ?? ''}
          onChange={(event) => change('status', event.target.value)}
        >
          <option value="">Все статусы</option>
          {Object.entries(statusLabels).map(([status, label]) => (
            <option key={status} value={status}>
              {label}
            </option>
          ))}
        </select>
        {(params.get('q') || params.get('department_id') || params.get('status')) && (
          <button className="clear-filters" onClick={() => setParams({})}>
            Сбросить
          </button>
        )}
      </div>
      {departments.isError && (
        <span className="filter-error" role="alert">
          Подразделения не загружены
        </span>
      )}
    </div>
  );
}
