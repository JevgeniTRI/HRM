import type { Currency, TaskDraft } from './types';

export function TaskCostFields({
  draft,
  change,
}: {
  draft: TaskDraft;
  change: (patch: Partial<TaskDraft>) => void;
}) {
  return (
    <fieldset className="task-form-section">
      <legend>Стоимость</legend>
      <div className="form-grid">
        <label>
          Стоимость всего
          <input
            aria-label="Стоимость всего"
            type="number"
            min="0"
            max="999999999.99"
            step="0.01"
            value={draft.cost}
            onChange={(event) => change({ cost: event.target.value })}
            placeholder="Не указана"
          />
        </label>
        <label>
          Валюта
          <select
            aria-label="Валюта стоимости"
            value={draft.currency}
            onChange={(event) => change({ currency: event.target.value as Currency })}
          >
            {(['EUR', 'USD', 'UAH', 'GBP'] as const).map((currency) => (
              <option key={currency}>{currency}</option>
            ))}
          </select>
        </label>
      </div>
      <p className="task-form-hint">
        Укажите общую стоимость, а не цену на участника. 0 означает бесплатно; пустое поле —
        стоимость неизвестна. Можно указать и стоимость, и человекочасы.
      </p>
    </fieldset>
  );
}
