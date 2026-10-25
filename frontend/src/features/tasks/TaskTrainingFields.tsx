import { useQuery } from '@tanstack/react-query';
import { Clock3 } from 'lucide-react';
import { useDebouncedValue } from '../../lib/useDebouncedValue';
import { taskApi } from './api';
import { decimalLabel } from './format';
import type { LearningFormat, LearningSource, TaskDraft } from './types';

export function TaskTrainingFields({
  draft,
  change,
}: {
  draft: TaskDraft;
  change: (patch: Partial<TaskDraft>) => void;
}) {
  const input = useDebouncedValue(`${draft.duration}|${draft.participants}`);
  const [hours, count] = input.split('|');
  const participants = Number(count);
  const valid =
    hours !== '' &&
    Number(hours) > 0 &&
    Number(hours) <= 10000 &&
    Number.isInteger(participants) &&
    participants >= 1 &&
    participants <= 10000;
  const estimate = useQuery({
    queryKey: ['task-estimate', hours, participants],
    queryFn: () => taskApi.estimate(hours, participants),
    enabled: valid,
    retry: false,
  });
  function changeFormat(format: LearningFormat) {
    change({
      format,
      participants:
        format === 'individual' ? '1' : String(Math.max(2, Number(draft.participants) || 2)),
    });
  }
  return (
    <fieldset className="task-form-section">
      <legend>Обучение</legend>
      <div className="form-grid">
        <label>
          Начало обучения
          <input
            type="date"
            value={draft.startOn}
            required={!!draft.endOn}
            max={draft.endOn || undefined}
            onChange={(event) => change({ startOn: event.target.value })}
          />
        </label>
        <label>
          Окончание обучения
          <input
            type="date"
            value={draft.endOn}
            required={!!draft.startOn}
            min={draft.startOn || undefined}
            onChange={(event) => change({ endOn: event.target.value })}
          />
        </label>
      </div>
      <p className="task-form-hint">
        Укажите обе даты, чтобы обучение появилось на диаграмме в календаре. Период включает день
        окончания; длительность в часах указывается отдельно.
      </p>
      <div className="form-grid">
        <label>
          Источник обучения
          <select
            aria-label="Источник обучения в карточке"
            value={draft.source}
            onChange={(event) => change({ source: event.target.value as LearningSource })}
          >
            <option value="internal">Внутреннее</option>
            <option value="external">Внешнее</option>
          </select>
        </label>
        <label>
          Формат обучения
          <select
            aria-label="Формат обучения в карточке"
            value={draft.format}
            onChange={(event) => changeFormat(event.target.value as LearningFormat)}
          >
            <option value="individual">Индивидуальное</option>
            <option value="group">Групповое</option>
          </select>
        </label>
      </div>
      <div className="form-grid">
        <label>
          Длительность, часов
          <input
            aria-label="Длительность, часов"
            type="number"
            min="0.01"
            max="10000"
            step="0.01"
            placeholder="Например, 1.5"
            value={draft.duration}
            onChange={(event) => change({ duration: event.target.value })}
          />
        </label>
        <label>
          Число участников
          <input
            aria-label="Число участников"
            type="number"
            required
            min={draft.format === 'group' ? 2 : 1}
            max="10000"
            step="1"
            disabled={draft.format === 'individual'}
            value={draft.participants}
            onChange={(event) => change({ participants: event.target.value })}
          />
        </label>
      </div>
      <div className="effort-preview" aria-live="polite">
        <Clock3 size={20} />
        <div>
          <span>Суммарная трудоёмкость</span>
          <strong>
            {!valid
              ? 'Укажите длительность и число участников'
              : estimate.isError
                ? 'Расчёт недоступен — проверьте значения'
                : estimate.isPending
                  ? 'Рассчитываем…'
                  : `${decimalLabel(estimate.data.person_hours)} человекочасов`}
          </strong>
          {valid && estimate.data && (
            <small>
              {decimalLabel(hours)} ч × {participants} участников ={' '}
              {decimalLabel(estimate.data.person_hours)} чел·ч
            </small>
          )}
        </div>
      </div>
      <p className="task-form-hint">
        Для завершённого обучения укажите фактическую длительность и число присутствовавших. Если
        длительность ещё неизвестна, поле можно оставить пустым.
      </p>
    </fieldset>
  );
}
