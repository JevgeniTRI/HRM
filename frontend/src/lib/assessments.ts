import type { Assessment } from '../types';

export type AssessmentState = 'unassigned' | 'unassessed' | 'met' | 'gap';

export function assessmentState(assessment?: Assessment): AssessmentState {
  return assessment?.state ?? 'unassigned';
}

export const assessmentLabels: Record<AssessmentState, string> = {
  unassigned: 'Не назначен',
  unassessed: 'Нужна оценка',
  met: 'Цель достигнута',
  gap: 'Зона развития',
};
