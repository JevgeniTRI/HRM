import { useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Download, FileText, Trash2, Upload } from 'lucide-react';
import type { Assessment, Certificate, Skill } from '../types';
import { api } from '../lib/api';
import { useRefreshData } from '../lib/queries';
import { FormError, Modal } from './ui';

export function CertificateList({
  employeeId,
  skillId,
  certificates,
  compact = false,
}: {
  employeeId: number;
  skillId: number;
  certificates: Certificate[];
  compact?: boolean;
}) {
  const refresh = useRefreshData();
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const remove = useMutation({
    mutationFn: (certificateId: number) =>
      api.deleteCertificate(employeeId, skillId, certificateId),
    onSuccess: async () => {
      setConfirmId(null);
      await refresh();
    },
  });
  if (!certificates.length) return <span className="muted">Сертификатов пока нет</span>;
  return (
    <div className={`certificate-list ${compact ? 'certificate-list-compact' : ''}`}>
      {certificates.map((certificate) => (
        <div className="certificate-item" key={certificate.id}>
          <a
            className="certificate-link"
            href={api.certificateUrl(employeeId, skillId, certificate.id)}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Просмотреть сертификат ${certificate.title}`}
          >
            <FileText size={17} />
            <span>
              <strong>{certificate.title}</strong>
              {!compact && (
                <small>
                  {certificate.original_name} ·{' '}
                  {certificate.size < 1024 * 1024
                    ? `${Math.max(1, Math.ceil(certificate.size / 1024))} КБ`
                    : `${(certificate.size / 1024 / 1024).toLocaleString('ru-RU', { maximumFractionDigits: 2 })} МБ`}
                </small>
              )}
            </span>
          </a>
          {!compact && (
            <div className="certificate-actions">
              <a
                className="icon-button"
                href={api.certificateUrl(employeeId, skillId, certificate.id, true)}
                aria-label={`Скачать сертификат ${certificate.title}`}
              >
                <Download size={16} />
              </a>
              {confirmId === certificate.id ? (
                <>
                  <button
                    type="button"
                    className="button text-danger compact"
                    disabled={remove.isPending}
                    onClick={() => remove.mutate(certificate.id)}
                  >
                    {remove.isPending ? 'Удаляем…' : 'Подтвердить удаление'}
                  </button>
                  <button
                    type="button"
                    className="button secondary compact"
                    disabled={remove.isPending}
                    onClick={() => setConfirmId(null)}
                  >
                    Отмена
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="icon-button delete-button"
                  disabled={remove.isPending}
                  aria-label={`Удалить сертификат ${certificate.title}`}
                  onClick={() => {
                    remove.reset();
                    setConfirmId(certificate.id);
                  }}
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          )}
        </div>
      ))}
      <FormError error={remove.error} />
    </div>
  );
}

export function CertificateUpload({
  employeeId,
  skills,
  initialSkillId,
  onSaved,
  onPendingChange,
}: {
  employeeId: number;
  skills: Skill[];
  initialSkillId?: number;
  onSaved?: () => void;
  onPendingChange?: (pending: boolean) => void;
}) {
  const refresh = useRefreshData();
  const input = useRef<HTMLInputElement>(null);
  const [skillId, setSkillId] = useState(
    String(initialSkillId ?? (skills.length === 1 ? skills[0].id : '')),
  );
  const [title, setTitle] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<Error | null>(null);
  const upload = useMutation({
    mutationFn: () => api.uploadCertificate(employeeId, Number(skillId), file!, title),
    onSuccess: async () => {
      setFile(null);
      setTitle('');
      if (input.current) input.current.value = '';
      await refresh();
      onSaved?.();
    },
    onSettled: () => onPendingChange?.(false),
  });
  function save() {
    if (upload.isPending || !file || !skillId) return;
    if (file.size === 0 || file.size > 10 * 1024 * 1024) {
      setValidation(new Error('Выберите непустой файл размером до 10 МБ.'));
      return;
    }
    if (!/\.(pdf|png|jpe?g|webp)$/i.test(file.name)) {
      setValidation(new Error('Допустимы файлы PDF, PNG, JPG и WebP.'));
      return;
    }
    setValidation(null);
    onPendingChange?.(true);
    upload.mutate();
  }
  return (
    <div className="certificate-upload">
      {skills.length > 1 ? (
        <label>
          Навык для сертификата
          <select
            value={skillId}
            disabled={upload.isPending}
            onChange={(event) => setSkillId(event.target.value)}
          >
            <option value="">Выберите навык</option>
            {skills.map((skill) => (
              <option key={skill.id} value={skill.id}>
                {skill.name}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <p className="field-hint">Навык: {skills[0]?.name}</p>
      )}
      <label>
        Название сертификата
        <input
          value={title}
          maxLength={160}
          disabled={upload.isPending}
          placeholder="Необязательно — по умолчанию имя файла"
          onChange={(event) => setTitle(event.target.value)}
        />
      </label>
      <label>
        Файл сертификата
        <input
          ref={input}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.webp"
          disabled={upload.isPending}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setValidation(null);
            upload.reset();
          }}
        />
      </label>
      <p className="field-hint">
        PDF, PNG, JPG или WebP · до 10 МБ. Можно добавить несколько сертификатов к одному навыку.
      </p>
      <FormError error={validation ?? upload.error} />
      <button
        type="button"
        className="button primary"
        disabled={upload.isPending || !file || !skillId}
        onClick={save}
      >
        <Upload size={16} />
        {upload.isPending ? 'Загружаем…' : 'Загрузить сертификат'}
      </button>
    </div>
  );
}

export function CertificateForm({
  employeeId,
  assessments,
  initialSkillId,
  onClose,
}: {
  employeeId: number;
  assessments: Assessment[];
  initialSkillId?: number;
  onClose: () => void;
}) {
  const [pending, setPending] = useState(false);
  return (
    <Modal
      title="Добавить сертификат"
      subtitle="Прикрепите документ к навыку сотрудника."
      onClose={() => {
        if (!pending) onClose();
      }}
    >
      <div className="modal-form">
        <CertificateUpload
          employeeId={employeeId}
          skills={assessments.map((item) => item.skill)}
          initialSkillId={initialSkillId}
          onSaved={onClose}
          onPendingChange={setPending}
        />
      </div>
    </Modal>
  );
}
