import { Search, SlidersHorizontal } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useDepartments } from '../../lib/queries';
import { useDebouncedValue } from '../../lib/useDebouncedValue';
import type { TaskFilters as Filters } from './types';

export function useTaskFilters(): Filters {
  const [params] = useSearchParams();
  const q = useDebouncedValue(params.get('q') ?? '');
  return {
    q,
    department_id: params.get('department_id') ?? '',
    learning_source: params.get('learning_source') ?? '',
    learning_format: params.get('learning_format') ?? '',
    is_training: params.get('is_training') ?? '',
  };
}

export function TaskFilters() {
  const [params, setParams] = useSearchParams();
  const departments = useDepartments();
  const filtered = ['q', 'department_id', 'learning_source', 'learning_format', 'is_training'].some(
    (key) => params.get(key),
  );
  function change(key: string, value: string) {
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (value) next.set(key, value);
        else next.delete(key);
        if (key === 'is_training' && value === 'false') {
          next.delete('learning_source');
          next.delete('learning_format');
        }
        if ((key === 'learning_source' || key === 'learning_format') && value)
          next.set('is_training', 'true');
        return next;
      },
      { replace: true },
    );
  }
  return (
    <section className="card task-filter-card" aria-label="Фильтры задач">
      <div className="filter-toolbar">
        <div className="filter-search">
          <Search size={17} />
          <input
            placeholder="Найти задачу или обучение…"
            aria-label="Поиск задач"
            maxLength={100}
            value={params.get('q') ?? ''}
            onChange={(event) => change('q', event.target.value)}
          />
        </div>
        <div className="filter-selects">
          <SlidersHorizontal size={17} />
          <select
            aria-label="Тип задачи"
            value={params.get('is_training') ?? ''}
            onChange={(event) => change('is_training', event.target.value)}
          >
            <option value="">Все задачи</option>
            <option value="true">Обучение</option>
            <option value="false">Обычные задачи</option>
          </select>
          <select
            aria-label="Источник обучения"
            value={params.get('learning_source') ?? ''}
            onChange={(event) => change('learning_source', event.target.value)}
          >
            <option value="">Любой источник</option>
            <option value="internal">Внутреннее</option>
            <option value="external">Внешнее</option>
          </select>
          <select
            aria-label="Формат обучения"
            value={params.get('learning_format') ?? ''}
            onChange={(event) => change('learning_format', event.target.value)}
          >
            <option value="">Любой формат</option>
            <option value="individual">Индивидуальное</option>
            <option value="group">Групповое</option>
          </select>
          <select
            aria-label="Подразделение задачи"
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
          {filtered && (
            <button className="clear-filters" onClick={() => setParams({})}>
              Сбросить
            </button>
          )}
        </div>
        {departments.isError && (
          <span className="filter-error" role="alert">
            Не удалось загрузить подразделения
          </span>
        )}
      </div>
    </section>
  );
}
