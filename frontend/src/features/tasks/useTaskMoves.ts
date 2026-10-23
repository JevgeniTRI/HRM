import { useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useRefreshData } from '../../lib/queries';
import { taskApi } from './api';
import type { PendingMove, Task, TaskStatus } from './types';

export function useTaskMoves() {
  const [moves, setMoves] = useState<PendingMove[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const busy = useRef(new Set<number>());
  const refresh = useRefreshData();
  const mutation = useMutation({
    mutationFn: ({ task, status }: PendingMove) => taskApi.move(task, status),
    onError: (error) => setError(error),
    onSettled: async (_, __, variables) => {
      await refresh();
      busy.current.delete(variables.task.id);
      setMoves((previous) => previous.filter((move) => move.task.id !== variables.task.id));
    },
  });
  function move(task: Task, status: TaskStatus) {
    if (task.status === status || busy.current.has(task.id)) return;
    setError(null);
    busy.current.add(task.id);
    setMoves((previous) => [...previous, { task, status }]);
    mutation.mutate({ task, status });
  }
  return { moves, move, error, clearError: () => setError(null) };
}
