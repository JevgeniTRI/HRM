import { useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import type { Assessment, Skill } from '../types';
import { api } from '../lib/api';
import {
  defaultScale,
  levelLabel,
  levelName,
  levelOption,
  scaleLabel,
  scaleLevels,
} from '../lib/skillScales';
import { useRefreshData, useSkills } from '../lib/queries';
import { ErrorState, FormError, Loading, Modal } from './ui';
import { CertificateList, CertificateUpload } from './Certificates';

export function AssessmentForm({
  employeeId,
  assessment,
  fixedSkill,
  assignedIds,
  onClose,
}: {
  employeeId: number;
  assessment?: Assessment;
  fixedSkill?: Skill;
  assignedIds?: number[];
  onClose: () => void;
}) {
  const skills = useSkills();
  const refresh = useRefreshData();
  const [skillId, setSkillId] = useState(String(assessment?.skill.id ?? fixedSkill?.id ?? ''));
  const [current, setCurrent] = useState(assessment?.current_level?.toString() ?? '');
  const [target, setTarget] = useState(String(assessment?.target_level ?? 3));
  const selectedSkill =
    skills.data?.find((item) => item.id === Number(skillId)) ?? assessment?.skill ?? fixedSkill;
  const scale = selectedSkill?.scale ?? defaultScale;
  const levels = scaleLevels(scale);
  const targetValue = Math.max(scale.min, Math.min(scale.max, Number(target)));
  const [uploadPending, setUploadPending] = useState(false);
  const employee = useQuery({
    queryKey: ['employee', employeeId],
    queryFn: () => api.employee(employeeId),
    enabled: !!assessment,
  });
  const certificates =
    employee.data?.skills.find((item) => item.skill.id === assessment?.skill.id)?.certificates ??
    assessment?.certificates ??
    [];
  const save = useMutation({
    mutationFn: () =>
      api.assess(employeeId, Number(skillId), current === '' ? null : Number(current), targetValue),
    onSuccess: async () => {
      await refresh();
      onClose();
    },
  });
  const remove = useMutation({
    mutationFn: () => api.removeAssessment(employeeId, Number(skillId)),
    onSuccess: async () => {
      await refresh();
      onClose();
    },
  });
  const pending = save.isPending || remove.isPending || uploadPending;
  const available = skills.data?.filter((skill) => !assignedIds?.includes(skill.id));
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!pending) save.mutate();
  }
  return (
    <Modal
      title={assessment ? 'Оценка навыка' : 'Добавить навык'}
      subtitle="Текущий уровень отражает опыт, целевой — ожидания от роли."
      onClose={() => {
        if (!pending) onClose();
      }}
    >
      {skills.isPending ? (
        <Loading />
      ) : skills.isError ? (
        <ErrorState error={skills.error} retry={() => skills.refetch()} />
      ) : (
        <form className="modal-form" onSubmit={submit}>
          <label>
            Навык
            {assessment || fixedSkill ? (
              <div className="readonly-field">{assessment?.skill.name ?? fixedSkill?.name}</div>
            ) : (
              <select
                autoFocus
                required
                value={skillId}
                onChange={(event) => {
                  setSkillId(event.target.value);
                  setCurrent('');
                  setTarget('3');
                }}
              >
                <option value="">Выберите навык</option>
                {available?.map((skill) => (
                  <option key={skill.id} value={skill.id}>
                    {skill.name}
                  </option>
                ))}
              </select>
            )}
          </label>
          {!assessment && !fixedSkill && !available?.length && (
            <p className="field-hint">Нет доступных навыков. Добавьте новый в каталог навыков.</p>
          )}
          <div className="form-grid">
            <label>
              Текущий уровень
              <select
                value={current}
                disabled={!skillId}
                onChange={(event) => setCurrent(event.target.value)}
              >
                <option value="">Не оценён</option>
                {levels.map((level) => (
                  <option key={level} value={level}>
                    {levelOption(scale, level)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Целевой уровень
              <select
                value={targetValue}
                disabled={!skillId}
                onChange={(event) => setTarget(event.target.value)}
              >
                {levels.map((level) => (
                  <option key={level} value={level}>
                    {levelOption(scale, level)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {selectedSkill && (
            <div className="level-guide">
              <p>
                Шкала {scaleLabel(scale)}.{' '}
                {scale.type === 'letter' && 'Уровни возрастают от A к Z. '}«Не оценён» означает, что
                оценка ещё не проведена.
              </p>
              <details className="assessment-scale-guide">
                <summary>Описания уровней</summary>
                <dl>
                  {levels.map((level) => (
                    <div key={level}>
                      <dt>{levelLabel(scale, level)}</dt>
                      <dd>
                        <strong>{levelName(scale, level)}</strong>
                        <p>
                          {scale.descriptions[String(level)] ||
                            'Требования к этому уровню пока не описаны.'}
                        </p>
                      </dd>
                    </div>
                  ))}
                </dl>
              </details>
            </div>
          )}
          <FormError error={save.error ?? remove.error} />
          {assessment && (
            <div className="assessment-certificates">
              <h3>Сертификаты навыка</h3>
              <CertificateList
                employeeId={employeeId}
                skillId={assessment.skill.id}
                certificates={certificates}
              />
              <CertificateUpload
                employeeId={employeeId}
                skills={[assessment.skill]}
                initialSkillId={assessment.skill.id}
                onPendingChange={setUploadPending}
              />
              {!!certificates.length && (
                <p className="field-hint">
                  При удалении навыка его сертификаты также будут удалены.
                </p>
              )}
            </div>
          )}
          <div className="modal-actions">
            {assessment && (
              <button
                type="button"
                className="button text-danger"
                disabled={pending}
                onClick={() => remove.mutate()}
              >
                Убрать навык
              </button>
            )}
            <button type="button" className="button secondary" disabled={pending} onClick={onClose}>
              Отмена
            </button>
            <button className="button primary" disabled={pending || !skillId}>
              {pending ? 'Сохраняем…' : 'Сохранить оценку'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
