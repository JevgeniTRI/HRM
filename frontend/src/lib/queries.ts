import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './api';

export const useDepartments = () =>
  useQuery({ queryKey: ['departments'], queryFn: api.departments });
export const useSkills = () => useQuery({ queryKey: ['skills'], queryFn: api.skills });
export function useRefreshData() {
  const client = useQueryClient();
  return () => client.invalidateQueries();
}
