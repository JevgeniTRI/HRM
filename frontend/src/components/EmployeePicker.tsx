import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useDebouncedValue } from '../lib/useDebouncedValue';
import { fullName } from '../lib/format';
import { FormError } from './ui';

export function EmployeePicker({
  value,
  onChange,
  required = false,
  label = 'Сотрудник',
  managersOnly = false,
  excludeId,
  emptyLabel = 'Не назначен',
  departmentId,
}: {
  value: number | null;
  onChange: (id: number | null) => void;
  required?: boolean;
  label?: string;
  managersOnly?: boolean;
  excludeId?: number;
  emptyLabel?: string;
  departmentId?: number;
}) {
  const [search, setSearch] = useState('');
  const q = useDebouncedValue(search);
  const list = useQuery({
    queryKey: ['employee-picker', q, managersOnly, departmentId],
    queryFn: () =>
      api.employees({
        q,
        page_size: 100,
        is_manager: managersOnly ? true : undefined,
        department_id: departmentId?.toString(),
      }),
  });
  const selected = useQuery({
    queryKey: ['employee', value],
    queryFn: () => api.employee(value!),
    enabled: value !== null,
  });
  const people = (list.data?.items ?? []).filter(
    (person) => person.id !== excludeId && (!departmentId || person.department_id === departmentId),
  );
  if (
    selected.data &&
    selected.data.id !== excludeId &&
    (!managersOnly || selected.data.is_manager) &&
    (!departmentId || selected.data.department_id === departmentId) &&
    !people.some((person) => person.id === value)
  )
    people.unshift(selected.data);
  return (
    <div className="employee-picker">
      <label>
        Поиск сотрудника
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          maxLength={100}
          placeholder="Имя, фамилия или email"
        />
      </label>
      <label>
        {label}
        <select
          required={required}
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
          disabled={list.isPending}
        >
          <option value="">{list.isPending ? 'Загружаем…' : emptyLabel}</option>
          {people.map((person) => (
            <option key={person.id} value={person.id}>
              {fullName(person)} · {person.department.name}
            </option>
          ))}
        </select>
      </label>
      {(list.data?.total ?? 0) > 100 && (
        <p className="field-hint">Уточните поиск, чтобы найти сотрудника.</p>
      )}
      <FormError error={list.error ?? selected.error} />
    </div>
  );
}
