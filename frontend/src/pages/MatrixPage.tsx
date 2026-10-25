import { useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Grid2X2, Info } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Assessment, Skill } from '../types';
import { api } from '../lib/api';
import { assessmentState } from '../lib/assessments';
import { levelLabel, levelOption, levelDescription, scaleLabel } from '../lib/skillScales';
import { fullName } from '../lib/format';
import { useEmployeeFilters } from '../lib/useEmployeeFilters';
import { AssessmentForm } from '../components/AssessmentForm';
import { EmployeeFilters } from '../components/EmployeeFilters';
import { Avatar, Empty, ErrorState, Loading, PageHeader, Pagination } from '../components/ui';

interface SelectedCell {
  employeeId: number;
  skill: Skill;
  assessment?: Assessment;
}

export function MatrixPage() {
  const [filters, setPage] = useEmployeeFilters(20);
  const matrix = useQuery({
    queryKey: ['matrix', filters],
    queryFn: () => api.matrix(filters),
    placeholderData: keepPreviousData,
  });
  const [cell, setCell] = useState<SelectedCell | null>(null);
  const [category, setCategory] = useState('');
  const categories = [...new Set(matrix.data?.skills.map((skill) => skill.category))];
  const skills =
    matrix.data?.skills.filter((skill) => !category || category === skill.category) ?? [];
  return (
    <>
      <PageHeader
        eyebrow="КАРТА КОМПЕТЕНЦИЙ"
        title="Матрица навыков"
        description="Видеть сильные стороны. Находить возможности для роста."
      >
        <select
          className="category-select"
          aria-label="Категория навыка"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        >
          <option value="">Все категории навыков</option>
          {categories.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </PageHeader>
      <section className="card list-card">
        <div className="list-title">
          <h2>
            <Grid2X2 size={19} />
            Компетенции команды
          </h2>
          <span>Нажмите на ячейку, чтобы изменить оценку</span>
        </div>
        <EmployeeFilters />
        {matrix.isPending ? (
          <Loading />
        ) : matrix.isError ? (
          <ErrorState error={matrix.error} retry={() => matrix.refetch()} />
        ) : !matrix.data.employees.length ? (
          <Empty
            title="Сотрудники не найдены"
            description="Добавьте сотрудников или измените фильтры."
          />
        ) : !skills.length ? (
          <Empty
            title="Нет навыков для отображения"
            description="Добавьте навыки в каталог или выберите другую категорию."
          />
        ) : (
          <div className={`table-scroll matrix-scroll ${matrix.isFetching ? 'is-fetching' : ''}`}>
            <table className="matrix-table">
              <thead>
                <tr>
                  <th>Сотрудник</th>
                  {skills.map((skill) => (
                    <th key={skill.id}>
                      <span>{skill.name}</span>
                      <small>
                        {skill.category} · {scaleLabel(skill.scale)}
                      </small>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.data.employees.map((employee) => (
                  <tr key={employee.id}>
                    <td>
                      <Link to={`/employees/${employee.id}`} className="person-cell">
                        <Avatar employee={employee} />
                        <div>
                          <strong>{fullName(employee)}</strong>
                          <small>{employee.department.name}</small>
                        </div>
                      </Link>
                    </td>
                    {skills.map((skill) => {
                      const assessment = employee.skills.find((item) => item.skill.id === skill.id);
                      const state = assessmentState(assessment);
                      const label = !assessment
                        ? 'не назначен'
                        : assessment.current_level === null
                          ? `не оценён, цель ${levelLabel(skill.scale, assessment.target_level)}`
                          : `уровень ${levelLabel(skill.scale, assessment.current_level)}, цель ${levelLabel(skill.scale, assessment.target_level)}`;
                      return (
                        <td key={skill.id}>
                          <button
                            className={`matrix-cell ${state}`}
                            title={`${skill.name}: ${label}${assessment ? `\nТекущий: ${assessment.current_level === null ? 'Не оценён' : `${levelOption(skill.scale, assessment.current_level)}\n${levelDescription(skill.scale, assessment.current_level)}`}\nЦель: ${levelOption(skill.scale, assessment.target_level)}\n${levelDescription(skill.scale, assessment.target_level)}` : ''}`}
                            aria-label={`${fullName(employee)}, ${skill.name}: ${label}`}
                            onClick={() => setCell({ employeeId: employee.id, skill, assessment })}
                          >
                            {!assessment ? (
                              '—'
                            ) : (
                              <>
                                <strong>
                                  {assessment.current_level === null
                                    ? '?'
                                    : levelLabel(skill.scale, assessment.current_level)}
                                </strong>
                                <span> / {levelLabel(skill.scale, assessment.target_level)}</span>
                              </>
                            )}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {matrix.data && (
          <Pagination
            page={filters.page ?? 1}
            total={matrix.data.total}
            pageSize={20}
            onChange={setPage}
          />
        )}
      </section>
      <div className="matrix-legend">
        <span>
          <i className="legend-dot green-dot" />
          Цель достигнута
        </span>
        <span>
          <i className="legend-dot amber-dot" />
          Ниже целевого уровня
        </span>
        <span>
          <i className="legend-dot purple-dot" />? — Не оценён
        </span>
        <span>
          <i className="legend-dot gray-dot" />— Навык не назначен
        </span>
        <span className="legend-explanation">
          <Info size={15} />
          Текущий уровень / цель
        </span>
      </div>
      {cell && (
        <AssessmentForm
          employeeId={cell.employeeId}
          assessment={cell.assessment}
          fixedSkill={cell.skill}
          onClose={() => setCell(null)}
        />
      )}
    </>
  );
}
