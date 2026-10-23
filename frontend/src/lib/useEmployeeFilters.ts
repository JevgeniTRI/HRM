import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { EmployeeFilters } from '../types';

export function useEmployeeFilters(pageSize: number): [EmployeeFilters, (page: number) => void] {
  const [params, setParams] = useSearchParams();
  const rawQuery = params.get('q') ?? '';
  const [query, setQuery] = useState(rawQuery);
  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(rawQuery), 250);
    return () => window.clearTimeout(timer);
  }, [rawQuery]);
  const rawPage = Number(params.get('page') ?? 1);
  const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const filters: EmployeeFilters = {
    q: query,
    department_id: params.get('department_id') ?? '',
    status: params.get('status') ?? '',
    page,
    page_size: pageSize,
  };
  function changePage(next: number) {
    setParams((previous) => {
      const value = new URLSearchParams(previous);
      value.set('page', String(next));
      return value;
    });
  }
  return [filters, changePage];
}
