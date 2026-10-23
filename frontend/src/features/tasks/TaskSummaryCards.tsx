import { CircleCheck, Clock3, Coins, ListTodo } from 'lucide-react';
import { ErrorState, Loading } from '../../components/ui';
import { costLabel, decimalLabel } from './format';
import type { TaskSummary } from './types';

export function TaskSummaryCards({
  summary,
  loading,
  error,
  retry,
}: {
  summary?: TaskSummary;
  loading: boolean;
  error: Error | null;
  retry: () => void;
}) {
  if (loading)
    return (
      <div className="card task-summary-loading">
        <Loading />
      </div>
    );
  if (error)
    return (
      <div className="card">
        <ErrorState error={error} retry={retry} />
      </div>
    );
  if (!summary) return null;
  return (
    <div className="metrics-grid task-metrics">
      <div className="metric-card">
        <div className="metric-top">
          <span>ЗАДАЧ НА ДОСКЕ</span>
          <span className="metric-icon lilac">
            <ListTodo size={18} />
          </span>
        </div>
        <div className="metric-value">{summary.total}</div>
        <p>С учётом выбранных фильтров</p>
      </div>
      <div className="metric-card">
        <div className="metric-top">
          <span>ЗАВЕРШЕНО</span>
          <span className="metric-icon green">
            <CircleCheck size={18} />
          </span>
        </div>
        <div className="metric-value">{summary.status_counts.done}</div>
        <p>
          {summary.status_counts.in_progress} в работе · {summary.status_counts.todo} запланировано
        </p>
      </div>
      <div className="metric-card">
        <div className="metric-top">
          <span>ЧЕЛОВЕКОЧАСЫ</span>
          <span className="metric-icon blue">
            <Clock3 size={18} />
          </span>
        </div>
        <div className="metric-value">
          {decimalLabel(summary.person_hours)}
          <small>чел·ч</small>
        </div>
        <p>
          {summary.unestimated_training_count
            ? `${summary.unestimated_training_count} обучений без длительности`
            : 'Сумма по всем статусам'}
        </p>
      </div>
      <div className="metric-card budget-metric">
        <div className="metric-top">
          <span>СТОИМОСТЬ ВСЕГО</span>
          <span className="metric-icon peach">
            <Coins size={18} />
          </span>
        </div>
        <div className="budget-values">
          {summary.costs.length ? (
            summary.costs.map((item) => (
              <strong key={item.currency}>{costLabel(item.amount, item.currency)}</strong>
            ))
          ) : (
            <strong>—</strong>
          )}
        </div>
        <p>{summary.without_cost_count} задач без стоимости · валюты отдельно</p>
      </div>
    </div>
  );
}
