import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import type { FormEvent } from 'react';
import type { Employee, EmployeeStatus } from '../types';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { statusLabels, todayISO } from '../lib/format';
import { useDepartments, useRefreshData } from '../lib/queries';
import { ErrorState, FormError, Loading, Modal } from './ui';

export function EmployeeForm({
  employee,
  onClose,
  onSaved,
}: {
  employee?: Employee;
  onClose: () => void;
  onSaved?: (id: number) => void;
}) {
  const { user, globalAccess } = useAuth();
  const departments = useDepartments();
  const refresh = useRefreshData();
  const [first, setFirst] = useState(employee?.first_name ?? '');
  const [last, setLast] = useState(employee?.last_name ?? '');
  const [email, setEmail] = useState(employee?.email ?? '');
  const [position, setPosition] = useState(employee?.position ?? '');
  const [department, setDepartment] = useState(employee?.department_id.toString() ?? '');
  const [status, setStatus] = useState<EmployeeStatus>(employee?.status ?? 'active');
  const [date, setDate] = useState(employee?.hired_at ?? todayISO());
  const [about, setAbout] = useState(employee?.about ?? '');
  const [experience, setExperience] = useState(employee?.experience ?? '');
  const [education, setEducation] = useState(employee?.education ?? '');
  const save = useMutation({
    mutationFn: () =>
      api.saveEmployee(
        {
          first_name: first.trim(),
          last_name: last.trim(),
          email: email.trim(),
          position: position.trim(),
          department_id: Number(department),
          status,
          hired_at: date,
          about,
          experience,
          education,
        },
        employee?.id,
      ),
    onSuccess: async (data) => {
      await refresh();
      onClose();
      onSaved?.(data.id);
    },
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!save.isPending) save.mutate();
  }
  return (
    <Modal
      title={employee ? 'Редактировать сотрудника' : 'Новый сотрудник'}
      subtitle="Заполните основные данные. Навыки можно добавить в карточке."
      onClose={() => {
        if (!save.isPending) onClose();
      }}
    >
      {departments.isPending ? (
        <Loading />
      ) : departments.isError ? (
        <ErrorState error={departments.error} retry={() => departments.refetch()} />
      ) : (
        <form className="modal-form" onSubmit={submit}>
          <div className="form-grid">
            <label>
              Имя
              <input
                autoFocus
                required
                maxLength={80}
                value={first}
                onChange={(event) => setFirst(event.target.value)}
                placeholder="Анна"
              />
            </label>
            <label>
              Фамилия
              <input
                required
                maxLength={80}
                value={last}
                onChange={(event) => setLast(event.target.value)}
                placeholder="Морозова"
              />
            </label>
          </div>
          <label>
            Рабочий email
            <input
              type="email"
              required
              maxLength={254}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="anna@company.com"
            />
          </label>
          <label>
            Должность
            <input
              required
              maxLength={120}
              value={position}
              disabled={user?.role === 'employee'}
              onChange={(event) => setPosition(event.target.value)}
              placeholder="Например, Frontend-разработчик"
            />
          </label>
          <label>
            Подразделение
            <select
              required
              value={department}
              disabled={!globalAccess}
              onChange={(event) => setDepartment(event.target.value)}
            >
              <option value="">Выберите подразделение</option>
              {departments.data?.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name}
                </option>
              ))}
            </select>
          </label>
          {!departments.data?.length && (
            <p className="field-hint">Сначала создайте подразделение в соответствующем разделе.</p>
          )}
          <div className="form-grid">
            <label>
              Статус
              <select
                value={status}
                disabled={user?.role === 'employee'}
                onChange={(event) => setStatus(event.target.value as EmployeeStatus)}
              >
                {Object.entries(statusLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Дата приёма
              <input
                type="date"
                required
                value={date}
                disabled={user?.role === 'employee'}
                onChange={(event) => setDate(event.target.value)}
              />
            </label>
          </div>
          <label>
            О себе
            <textarea
              rows={3}
              maxLength={5000}
              value={about}
              onChange={(e) => setAbout(e.target.value)}
              placeholder="Профессиональные интересы и сильные стороны"
            />
          </label>
          <label>
            Опыт работы
            <textarea
              rows={4}
              maxLength={10000}
              value={experience}
              onChange={(e) => setExperience(e.target.value)}
              placeholder="Проекты, обязанности и достижения"
            />
          </label>
          <label>
            Образование
            <textarea
              rows={3}
              maxLength={5000}
              value={education}
              onChange={(e) => setEducation(e.target.value)}
              placeholder="Учебные заведения и дополнительное обучение"
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
            <button
              className="button primary"
              disabled={save.isPending || !departments.data?.length}
            >
              {save.isPending ? 'Сохраняем…' : employee ? 'Сохранить' : 'Добавить сотрудника'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
