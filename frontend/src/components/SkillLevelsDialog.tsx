import type { Assessment } from '../types';
import { levelLabel, levelName, scaleLabel, scaleLevels } from '../lib/skillScales';
import { Modal } from './ui';

export function SkillLevelsDialog({
  assessment,
  onClose,
}: {
  assessment: Assessment;
  onClose: () => void;
}) {
  const { skill } = assessment;
  return (
    <Modal
      title={`${skill.name}: уровни компетенции`}
      subtitle={`Шкала ${scaleLabel(skill.scale)} · Требования ко всем уровням`}
      onClose={onClose}
      wide
    >
      <div className="skill-levels-dialog">
        <ol className="skill-level-reference">
          {scaleLevels(skill.scale).map((level) => (
            <li
              key={level}
              className={assessment.current_level === level ? 'is-current-level' : ''}
            >
              <span className="skill-level-code">{levelLabel(skill.scale, level)}</span>
              <div className="skill-level-reference-content">
                <h3>{levelName(skill.scale, level)}</h3>
                <div className="skill-level-markers">
                  {assessment.current_level === level && <span>Текущий уровень</span>}
                  {assessment.target_level === level && <span>Целевой уровень</span>}
                </div>
                <p>
                  {skill.scale.descriptions[String(level)] ||
                    'Требования к этому уровню пока не описаны.'}
                </p>
              </div>
            </li>
          ))}
        </ol>
        <div className="modal-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            Закрыть
          </button>
        </div>
      </div>
    </Modal>
  );
}
