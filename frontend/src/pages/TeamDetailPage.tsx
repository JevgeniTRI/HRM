import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, Plus, Repeat2, Trash2 } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { teamsApi } from '../lib/teams';
import { useAuth } from '../lib/auth';
import { fullName } from '../lib/format';
import { useRefreshData } from '../lib/queries';
import { Empty, ErrorState, FormError, Loading, PageHeader, Pagination } from '../components/ui';
import { AssignTeamMembers, ReplaceTeamManager } from '../components/TeamForms';
import { DeleteDialog } from '../components/CatalogForm';

export function TeamDetailPage() {
  const id = Number(useParams().id);
  const [page, setPage] = useState(1);
  const team = useQuery({ queryKey: ['team', id], queryFn: () => teamsApi.read(id) });
  const people = useQuery({
    queryKey: ['team-members', id, page],
    queryFn: () => teamsApi.members(id, page),
  });
  const { globalAccess } = useAuth();
  const [assign, setAssign] = useState(false);
  const [replace, setReplace] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const refresh = useRefreshData();
  const navigate = useNavigate();
  const remove = useMutation({
    mutationFn: (personId: number) => teamsApi.remove(team.data!, personId),
    onSuccess: async () => {
      setPage(1);
      await refresh();
    },
  });
  if (team.isPending) return <Loading />;
  if (team.isError) return <ErrorState error={team.error} retry={() => team.refetch()} />;
  const item = team.data;
  return (
    <>
      <Link to="/teams" className="back-link">
        <ArrowLeft size={16} />
        Все команды
      </Link>
      <PageHeader title={item.name} description={`${item.code} · ${item.department.name}`}>
        {globalAccess && (
          <>
            <button className="button secondary" onClick={() => setReplace(true)}>
              <Repeat2 size={17} />
              {item.manager ? 'Заменить руководителя' : 'Назначить руководителя'}
            </button>
            <button className="button primary" onClick={() => setAssign(true)}>
              <Plus size={17} />
              Добавить сотрудников
            </button>
            <button
              className="icon-button delete-button"
              aria-label="Удалить команду"
              onClick={() => setDeleting(true)}
            >
              <Trash2 size={17} />
            </button>
          </>
        )}
      </PageHeader>
      <section className="card team-summary" aria-label="Руководство команды">
        <div>
          <span>Руководитель команды</span>
          <strong>{item.manager ? fullName(item.manager) : 'Пока не назначен'}</strong>
        </div>
        <div>
          <span>Вышестоящий руководитель</span>
          <strong>{item.supervisor ? fullName(item.supervisor) : 'Не назначен'}</strong>
        </div>
        <div>
          <span>Участников команды</span>
          <strong>{item.member_count}</strong>
        </div>
      </section>
      <section className="card">
        <div className="card-heading">
          <div>
            <h2>
              Состав команды <span className="count-tag">{item.member_count}</span>
            </h2>
            <p>Руководитель команды указан отдельно от участников.</p>
          </div>
        </div>
        <FormError error={remove.error} />
        {people.isPending ? (
          <Loading />
        ) : people.isError ? (
          <ErrorState error={people.error} retry={() => people.refetch()} />
        ) : !people.data.items.length ? (
          <Empty
            title="В команде пока нет сотрудников"
            description="Добавьте сотрудников списком или импортируйте файл с кодом этой команды."
          />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Сотрудник</th>
                  <th>Должность</th>
                  <th>Email</th>
                  {globalAccess && <th />}
                </tr>
              </thead>
              <tbody>
                {people.data.items.map((person) => (
                  <tr key={person.id}>
                    <td>
                      <Link to={`/employees/${person.id}`}>{fullName(person)}</Link>
                    </td>
                    <td>{person.position}</td>
                    <td>{person.email}</td>
                    {globalAccess && (
                      <td>
                        <button
                          className="button secondary compact"
                          disabled={remove.isPending}
                          onClick={() => remove.mutate(person.id)}
                          title="Сотрудник останется без команды и непосредственного руководителя"
                        >
                          Вывести из команды
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {people.data && (
          <Pagination page={page} total={people.data.total} pageSize={50} onChange={setPage} />
        )}
      </section>
      {assign && <AssignTeamMembers team={item} onClose={() => setAssign(false)} />}
      {replace && <ReplaceTeamManager team={item} onClose={() => setReplace(false)} />}
      {deleting && (
        <DeleteDialog
          title="Удалить команду?"
          description="Удалить можно только пустую команду. Карточки руководителей и сотрудников сохраняются."
          onDelete={async () => {
            await teamsApi.delete(item);
            navigate('/teams');
          }}
          onClose={() => setDeleting(false)}
        />
      )}
    </>
  );
}
