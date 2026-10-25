import type { SkillScale } from '../types';

export const defaultScale: SkillScale = {
  type: 'numeric',
  min: 0,
  max: 5,
  names: {
    '0': 'Нет опыта',
    '1': 'Начальный',
    '2': 'Базовый',
    '3': 'Уверенный',
    '4': 'Продвинутый',
    '5': 'Эксперт',
  },
  descriptions: {},
};
export const scaleLevels = (scale: SkillScale) =>
  Array.from({ length: scale.max - scale.min + 1 }, (_, index) => scale.min + index);
export const levelLabel = (scale: SkillScale, level: number) =>
  scale.type === 'letter'
    ? String.fromCharCode(65 + Math.round(level))
    : new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 }).format(level);
export const levelDescription = (scale: SkillScale, level: number) =>
  scale.descriptions[String(level)] || '';
export const levelName = (scale: SkillScale, level: number) =>
  scale.names?.[String(level)] || `Уровень ${levelLabel(scale, level)}`;
export const levelOption = (scale: SkillScale, level: number) => {
  return `${levelLabel(scale, level)} — ${levelName(scale, level)}`;
};
export const scaleLabel = (scale: SkillScale) =>
  `${levelLabel(scale, scale.min)}–${levelLabel(scale, scale.max)}`;
