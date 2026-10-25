import { ArrowRight, ArrowUpRight, BookOpen } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { SkillMetric } from '../../types';
import { Empty } from '../ui';
import { levelLabel } from '../../lib/skillScales';

export function SkillOverview({ metrics }: { metrics: SkillMetric[] }) {
  return (
    <section className="card skills-overview">
      <div className="card-heading">
        <div>
          <h2>Пульс навыков</h2>
          <p>Как текущие уровни соотносятся с целями команды</p>
        </div>
        <Link to="/matrix" className="button secondary compact">
          Матрица навыков
          <ArrowUpRight size={15} />
        </Link>
      </div>
      {!metrics.length ? (
        <Empty
          title="Начните с каталога навыков"
          description="Добавьте навыки и назначьте их сотрудникам."
        />
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Навык</th>
                <th>Категория</th>
                <th>Сотрудников</th>
                <th>Средний уровень</th>
                <th>Достигли цели</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {metrics.slice(0, 5).map((metric) => (
                <tr key={metric.id}>
                  <td>
                    <span className="skill-table-name">
                      <span className="small-skill-icon">
                        <BookOpen size={15} />
                      </span>
                      <strong>{metric.name}</strong>
                    </span>
                  </td>
                  <td>
                    <span className="category-tag">{metric.category}</span>
                  </td>
                  <td>
                    {metric.assigned}
                    <span className="muted"> чел.</span>
                  </td>
                  <td>
                    <div className="level-display">
                      <strong>
                        {metric.average_level === null
                          ? '—'
                          : levelLabel(metric.scale, metric.average_level)}
                      </strong>
                      <span className="level-dots" aria-hidden="true">
                        {[1, 2, 3, 4, 5].map((index) => (
                          <i
                            key={index}
                            className={
                              metric.average_level !== null &&
                              index <=
                                Math.round(
                                  (metric.scale.max === metric.scale.min
                                    ? 1
                                    : (metric.average_level - metric.scale.min) /
                                      (metric.scale.max - metric.scale.min)) * 5,
                                )
                                ? 'filled'
                                : ''
                            }
                          />
                        ))}
                      </span>
                      <span className="muted">/ {levelLabel(metric.scale, metric.scale.max)}</span>
                    </div>
                  </td>
                  <td>
                    <div className="coverage-cell">
                      <span className="mini-progress" aria-hidden="true">
                        <i
                          style={{
                            width: `${metric.coverage}%`,
                          }}
                        />
                      </span>
                      <strong>
                        {metric.at_target}
                        <span className="muted"> / {metric.assigned}</span>
                      </strong>
                    </div>
                  </td>
                  <td>
                    <Link
                      to="/matrix"
                      className="icon-link"
                      aria-label={`Посмотреть навык ${metric.name}`}
                    >
                      <ArrowUpRight size={17} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="overview-bottom">
        <span>
          <i className="legend-dot green-dot" />
          Цель достигнута при текущем уровне ≥ целевого
        </span>
        <Link to="/skills">
          Все навыки
          <ArrowRight size={14} />
        </Link>
      </div>
    </section>
  );
}
