import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowRight, Plus, Upload, Users } from 'lucide-react';
import { teamsApi } from '../lib/teams';
import { useDepartments } from '../lib/queries';
import { useAuth } from '../lib/auth';
import { fullName } from '../lib/format';
import { useDebouncedValue } from '../lib/useDebouncedValue';
import { Empty, ErrorState, Loading, PageHeader } from '../components/ui';
import { TeamForm, TeamImportDialog } from '../components/TeamForms';

export function TeamsPage() {
  const { globalAccess } = useAuth();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const q = useDebouncedValue(search);
  const department = params.get('department_id') ?? '';
  const departments = useDepartments();
  const teams = useQuery({
    queryKey: ['teams', department, q],
    queryFn: () => teamsApi.list({ department_id: department, q }),
  });
  const [create, setCreate] = useState(false);
  const [importing, setImporting] = useState(false);
  return (
    <>
      <PageHeader
        eyebrow="СТРУКТУРА ОРГАНИЗАЦИИ"
        title="Команды"
        description="Состав команды сохраняется при замене руководителя."
      >
        {globalAccess && (
          <>
            <Link className="button secondary" to="/imports">
              Общий импорт
            </Link>
            <button className="button secondary" onClick={() => setImporting(true)}>
              <Upload size={17} />
              Импорт Excel / CSV
            </button>
            <button className="button primary" onClick={() => setCreate(true)}>
              <Plus size={17} />
              Создать команду
            </button>
          </>
        )}
      </PageHeader>
      <div className="card team-filters">
        <label>
          Поиск команд
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            maxLength={100}
            placeholder="Название или код"
          />
        </label>
        <label>
          Отдел
          <select
            value={department}
            onChange={(event) =>
              setParams(event.target.value ? { department_id: event.target.value } : {})
            }
          >
            <option value="">Все доступные отделы</option>
            {departments.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {teams.isPending ? (
        <Loading />
      ) : teams.isError ? (
        <ErrorState error={teams.error} retry={() => teams.refetch()} />
      ) : !teams.data.length ? (
        <section className="card">
          <Empty
            title="Команд пока нет"
            description={
              globalAccess
                ? 'Создайте команду, затем назначьте сотрудников списком или загрузите Excel / CSV.'
                : 'В вашей ветке подчинения пока нет команд.'
            }
          />
        </section>
      ) : (
        <div className="catalog-grid">
          {teams.data.map((team) => (
            <article className="card catalog-card" key={team.id}>
              <span className="count-tag">{team.code}</span>
              <h2>{team.name}</h2>
              <p>{team.department.name}</p>
              <p>
                Руководитель:{' '}
                <strong>{team.manager ? fullName(team.manager) : 'Не назначен'}</strong>
              </p>
              <p>
                <Users size={16} /> Участников: {team.member_count}
              </p>
              <Link className="catalog-card-footer" to={`/teams/${team.id}`}>
                Открыть команду <ArrowRight size={16} />
              </Link>
            </article>
          ))}
        </div>
      )}
      {create && <TeamForm onClose={() => setCreate(false)} />}
      {importing && <TeamImportDialog onClose={() => setImporting(false)} />}
    </>
  );
}
