import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useRefreshData } from '../lib/queries';
import { FormError, Modal } from './ui';

interface CatalogValues {
  name: string;
  description: string;
  category: string;
}
interface CatalogFormProps {
  title: string;
  initial?: Partial<CatalogValues>;
  withCategory?: boolean;
  onSave: (data: CatalogValues) => Promise<unknown>;
  onClose: () => void;
}

export function CatalogForm({ title, initial, withCategory, onSave, onClose }: CatalogFormProps) {
  const [name, setName] = useState(initial?.name ?? '');
  const [description, setDescription] = useState(initial?.description ?? '');
  const [category, setCategory] = useState(initial?.category ?? '');
  const refresh = useRefreshData();
  const save = useMutation({
    mutationFn: () =>
      onSave({ name: name.trim(), description: description.trim(), category: category.trim() }),
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
      title={title}
      onClose={() => {
        if (!save.isPending) onClose();
      }}
    >
      <form className="modal-form" onSubmit={submit}>
        <label>
          Название
          <input
            autoFocus
            required
            maxLength={100}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={withCategory ? 'Например, Python' : 'Например, Разработка'}
          />
        </label>
        {withCategory && (
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
        )}
        <label>
          Описание<span className="optional-label">необязательно</span>
          <textarea
            rows={4}
            maxLength={2000}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Краткое описание…"
          />
        </label>
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

export function DeleteDialog({
  title,
  description,
  onDelete,
  onClose,
}: {
  title: string;
  description: string;
  onDelete: () => Promise<void>;
  onClose: () => void;
}) {
  const refresh = useRefreshData();
  const remove = useMutation({
    mutationFn: onDelete,
    onSuccess: async () => {
      await refresh();
      onClose();
    },
  });
  return (
    <Modal
      title={title}
      onClose={() => {
        if (!remove.isPending) onClose();
      }}
    >
      <div className="modal-form">
        <p>{description}</p>
        <FormError error={remove.error} />
        <div className="modal-actions">
          <button className="button secondary" disabled={remove.isPending} onClick={onClose}>
            Отмена
          </button>
          <button
            className="button danger"
            disabled={remove.isPending}
            onClick={() => remove.mutate()}
          >
            {remove.isPending ? 'Удаляем…' : 'Удалить'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
