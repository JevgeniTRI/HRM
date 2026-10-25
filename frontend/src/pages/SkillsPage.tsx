import { useState } from 'react';
import { BookOpen, Pencil, Plus, Search, Trash2, Users } from 'lucide-react';
import type { Skill } from '../types';
import { api } from '../lib/api';
import { useSkills } from '../lib/queries';
import { DeleteDialog } from '../components/CatalogForm';
import { SkillForm } from '../components/SkillForm';
import { scaleLabel } from '../lib/skillScales';
import { Empty, ErrorState, Loading, PageHeader } from '../components/ui';

export function SkillsPage() {
  const skills = useSkills();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [edit, setEdit] = useState<Skill | 'new' | null>(null);
  const [remove, setRemove] = useState<Skill | null>(null);
  const categories = [...new Set(skills.data?.map((skill) => skill.category))];
  const filtered = skills.data?.filter(
    (skill) =>
      (!category || skill.category === category) &&
      `${skill.name} ${skill.description}`
        .toLocaleLowerCase('ru')
        .includes(search.toLocaleLowerCase('ru')),
  );
  return (
    <>
      <PageHeader
        eyebrow="КОМПЕТЕНЦИИ И РАЗВИТИЕ"
        title="Навыки"
        description="Единый каталог компетенций вашей команды."
      >
        <button className="button primary" onClick={() => setEdit('new')}>
          <Plus size={18} />
          Добавить навык
        </button>
      </PageHeader>
      <div className="catalog-toolbar">
        <div className="filter-search">
          <Search size={17} />
          <input
            aria-label="Поиск навыков"
            placeholder="Найти навык…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <select
          aria-label="Категория навыка"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        >
          <option value="">Все категории</option>
          {categories.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <span className="catalog-count">{filtered?.length ?? 0} навыков</span>
      </div>
      {skills.isPending ? (
        <Loading />
      ) : skills.isError ? (
        <ErrorState error={skills.error} retry={() => skills.refetch()} />
      ) : !filtered?.length ? (
        <section className="card">
          <Empty
            title="Навыки не найдены"
            description="Измените фильтры или добавьте новый навык."
          />
        </section>
      ) : (
        <div className="catalog-grid">
          {filtered.map((skill) => (
            <article className="card catalog-card" key={skill.id}>
              <div className="catalog-card-top">
                <span className="catalog-icon lilac">
                  <BookOpen size={22} strokeWidth={1.6} />
                </span>
                <div>
                  <button
                    className="icon-button"
                    onClick={() => setEdit(skill)}
                    aria-label={`Редактировать ${skill.name}`}
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    className="icon-button"
                    onClick={() => setRemove(skill)}
                    aria-label={`Удалить ${skill.name}`}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <h2>{skill.name}</h2>
              <span className="category-tag">{skill.category}</span>
              <p>{skill.description || 'Описание ещё не добавлено.'}</p>
              <div className="catalog-card-footer">
                <span>
                  <Users size={15} />
                  {skill.employee_count} сотрудников
                </span>
                <span>Шкала {scaleLabel(skill.scale)}</span>
              </div>
            </article>
          ))}
        </div>
      )}
      <div className="info-note">
        <BookOpen size={18} />
        <p>
          Для каждого навыка можно настроить числовую шкалу в пределах 0–10 или буквенную A–Z и
          описать каждый уровень. Настройка доступна администратору и power_user. Целевой уровень
          задаётся индивидуально в карточке сотрудника.
        </p>
      </div>
      {edit && (
        <SkillForm skill={edit === 'new' ? undefined : edit} onClose={() => setEdit(null)} />
      )}
      {remove && (
        <DeleteDialog
          title="Удалить навык?"
          description={`Навык «${remove.name}» можно удалить, если он не назначен сотрудникам.`}
          onDelete={() => api.deleteSkill(remove.id)}
          onClose={() => setRemove(null)}
        />
      )}
    </>
  );
}
