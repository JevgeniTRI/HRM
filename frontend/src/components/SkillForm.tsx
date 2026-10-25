import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useRefreshData } from '../lib/queries';
import { defaultScale, levelLabel, scaleLevels } from '../lib/skillScales';
import type { Skill, SkillScale } from '../types';
import { FormError, Modal } from './ui';

export function SkillForm({ skill, onClose }: { skill?: Skill; onClose: () => void }) {
  const [name, setName] = useState(skill?.name ?? '');
  const [category, setCategory] = useState(skill?.category ?? '');
  const [description, setDescription] = useState(skill?.description ?? '');
  const [scale, setScale] = useState<SkillScale>(
    () => skill?.scale ?? { ...defaultScale, max: 10 },
  );
  const refresh = useRefreshData();
  const levels = scaleLevels(scale);
  const choices = scaleLevels({ ...scale, min: 0, max: scale.type === 'numeric' ? 10 : 25 });
  const save = useMutation({
    mutationFn: () =>
      api.saveSkill(
        {
          name: name.trim(),
          category: category.trim(),
          description: description.trim(),
          scale: {
            ...scale,
            names: Object.fromEntries(
              levels.map((level) => [String(level), scale.names?.[String(level)]?.trim() ?? '']),
            ),
            descriptions: Object.fromEntries(
              levels.map((level) => [
                String(level),
                scale.descriptions[String(level)]?.trim() ?? '',
              ]),
            ),
          },
        },
        skill?.id,
      ),
    onSuccess: async () => {
      await refresh();
      onClose();
    },
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!save.isPending) save.mutate();
  }
  return (
    <Modal
      title={skill ? 'Редактировать навык' : 'Новый навык'}
      onClose={() => {
        if (!save.isPending) onClose();
      }}
      wide
    >
      <form className="modal-form skill-form" onSubmit={submit}>
        <fieldset className="skill-form-controls" disabled={save.isPending}>
          <label>
            Название
            <input
              autoFocus
              required
              maxLength={100}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Например, Excel"
            />
          </label>
          <label>
            Категория
            <input
              required
              maxLength={80}
              list="skill-categories"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              placeholder="Выберите или введите категорию"
            />
            <datalist id="skill-categories">
              {['Технические', 'Гибкие навыки', 'Дизайн', 'Управление', 'Языки'].map((item) => (
                <option key={item} value={item} />
              ))}
            </datalist>
          </label>
          <label>
            Описание<span className="optional-label">необязательно</span>
            <textarea
              aria-label="Описание навыка"
              rows={3}
              maxLength={2000}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Краткое описание навыка…"
            />
          </label>
          <fieldset className="skill-scale-settings">
            <legend>Шкала уровней</legend>
            <label>
              Тип шкалы
              <select
                value={scale.type}
                onChange={(event) => {
                  const type = event.target.value as SkillScale['type'];
                  setScale((previous) => ({
                    ...previous,
                    type,
                    min: 0,
                    max: type === 'numeric' ? 10 : 25,
                  }));
                }}
              >
                <option value="numeric">Числовая (0–10)</option>
                <option value="letter">Буквенная (A–Z)</option>
              </select>
            </label>
            <div className="form-grid">
              <label>
                Начало диапазона
                <select
                  value={scale.min}
                  onChange={(event) => {
                    const min = Number(event.target.value);
                    setScale((previous) => ({
                      ...previous,
                      min,
                      max: Math.max(min, previous.max),
                    }));
                  }}
                >
                  {choices.map((level) => (
                    <option key={level} value={level}>
                      {levelLabel(scale, level)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Конец диапазона
                <select
                  value={scale.max}
                  onChange={(event) => {
                    const max = Number(event.target.value);
                    setScale((previous) => ({
                      ...previous,
                      max,
                      min: Math.min(max, previous.min),
                    }));
                  }}
                >
                  {choices.map((level) => (
                    <option key={level} value={level}>
                      {levelLabel(scale, level)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="field-hint">
              {scale.type === 'letter'
                ? 'Уровни возрастают от A к Z: A — минимальный, Z — максимальный.'
                : 'Уровни возрастают от меньшего числа к большему.'}{' '}
              «Не оценён» остаётся отдельным состоянием.
            </p>
            {skill && (
              <p className="field-hint">
                Диапазон должен включать существующие оценки и цели. При смене типа оценки сохраняют
                позицию: 0 → A, 1 → B и далее.
              </p>
            )}
          </fieldset>
          <div className="skill-level-heading">
            <h3>Названия и описания уровней</h3>
            <span>{levels.length} уровней</span>
          </div>
          <div className="skill-level-editors">
            {levels.map((level) => (
              <div key={level} className="skill-level-editor">
                <span className="skill-level-code">{levelLabel(scale, level)}</span>
                <div className="skill-level-fields">
                  <label>
                    Название уровня
                    <input
                      aria-label={`Название уровня ${levelLabel(scale, level)}`}
                      maxLength={100}
                      value={scale.names?.[String(level)] ?? ''}
                      placeholder="Например, Базовый или Продвинутый"
                      onChange={(event) =>
                        setScale((previous) => ({
                          ...previous,
                          names: { ...previous.names, [String(level)]: event.target.value },
                        }))
                      }
                    />
                  </label>
                  <label>
                    Описание уровня
                    <textarea
                      aria-label={`Описание уровня ${levelLabel(scale, level)}`}
                      rows={2}
                      maxLength={1000}
                      value={scale.descriptions[String(level)] ?? ''}
                      placeholder="Что знает и умеет сотрудник на этом уровне"
                      onChange={(event) =>
                        setScale((previous) => ({
                          ...previous,
                          descriptions: {
                            ...previous.descriptions,
                            [String(level)]: event.target.value,
                          },
                        }))
                      }
                    />
                  </label>
                </div>
              </div>
            ))}
          </div>
        </fieldset>
        <FormError error={save.error} />
        <div className="modal-actions">
          <button
            type="button"
            className="button secondary"
            disabled={save.isPending}
            onClick={onClose}
          >
            Отмена
          </button>
          <button className="button primary" disabled={save.isPending}>
            {save.isPending ? 'Сохраняем…' : 'Сохранить'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
