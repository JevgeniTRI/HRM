import { useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Camera, Trash2, Upload } from 'lucide-react';
import type { Employee } from '../types';
import { api } from '../lib/api';
import { useRefreshData } from '../lib/queries';
import { Avatar, FormError } from './ui';

export function ProfilePhoto({ employee, canEdit }: { employee: Employee; canEdit: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const refresh = useRefreshData();
  const [validation, setValidation] = useState<Error | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const upload = useMutation({
    mutationFn: (file: File) => api.uploadEmployeePhoto(employee.id, file),
    onSuccess: async () => {
      if (input.current) input.current.value = '';
      await refresh();
    },
  });
  const remove = useMutation({
    mutationFn: () => api.deleteEmployeePhoto(employee.id),
    onSuccess: async () => {
      setConfirmDelete(false);
      await refresh();
    },
  });
  function selectPhoto(file: File | undefined) {
    upload.reset();
    remove.reset();
    setConfirmDelete(false);
    if (!file) return;
    if (!/\.(png|jpe?g|webp)$/i.test(file.name)) {
      setValidation(new Error('Допустимы фотографии PNG, JPG и WebP.'));
      return;
    }
    if (file.size === 0 || file.size > 5 * 1024 * 1024) {
      setValidation(new Error('Выберите непустую фотографию размером до 5 МБ.'));
      return;
    }
    setValidation(null);
    upload.mutate(file);
  }
  const pending = upload.isPending || remove.isPending;
  return (
    <div className="profile-photo-control">
      <Avatar employee={employee} size="large" />
      {canEdit && (
        <>
          <input
            ref={input}
            className="profile-photo-input"
            type="file"
            accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
            disabled={pending}
            aria-label="Выбрать фотографию профиля"
            onChange={(event) => selectPhoto(event.target.files?.[0])}
          />
          <div className="profile-photo-actions">
            <button
              type="button"
              className="button secondary compact"
              disabled={pending}
              onClick={() => input.current?.click()}
            >
              {employee.has_photo ? <Camera size={14} /> : <Upload size={14} />}
              {upload.isPending
                ? 'Загружаем…'
                : employee.has_photo
                  ? 'Изменить фото'
                  : 'Добавить фото'}
            </button>
            {employee.has_photo &&
              (confirmDelete ? (
                <div className="profile-photo-confirm">
                  <button
                    type="button"
                    className="button text-danger compact"
                    disabled={pending}
                    onClick={() => remove.mutate()}
                  >
                    {remove.isPending ? 'Удаляем…' : 'Удалить'}
                  </button>
                  <button
                    type="button"
                    className="button secondary compact"
                    disabled={pending}
                    onClick={() => setConfirmDelete(false)}
                  >
                    Отмена
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  className="button secondary compact profile-photo-delete"
                  disabled={pending}
                  onClick={() => setConfirmDelete(true)}
                >
                  <Trash2 size={14} /> Удалить
                </button>
              ))}
          </div>
          <FormError error={validation ?? upload.error ?? remove.error} />
          <span className="profile-photo-hint">PNG, JPG или WebP · до 5 МБ</span>
        </>
      )}
    </div>
  );
}
