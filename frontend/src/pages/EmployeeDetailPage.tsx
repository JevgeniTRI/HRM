import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  BookOpen,
  Building2,
  CalendarDays,
  Mail,
  Pencil,
  Plus,
  Target,
  Trash2,
} from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import type { Assessment } from '../types';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { assessmentLabels, assessmentState } from '../lib/assessments';
import { dateLabel, fullName, levelLabels, timestamp } from '../lib/format';
import { useRefreshData } from '../lib/queries';
import {
  Avatar,
  Empty,
  ErrorState,
  FormError,
  Loading,
  Modal,
  PageHeader,
  StatusBadge,
} from '../components/ui';
import { EmployeeForm } from '../components/EmployeeForm';
import { AssessmentForm } from '../components/AssessmentForm';
import { CertificateForm, CertificateList } from '../components/Certificates';

export function EmployeeDetailPage() {
  const { user, globalAccess } = useAuth();
  const id = Number(useParams().id);
  const employee = useQuery({ queryKey: ['employee', id], queryFn: () => api.employee(id) });
  const [edit, setEdit] = useState(false);
  const [assessment, setAssessment] = useState<Assessment | 'new' | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [certificateSkillId, setCertificateSkillId] = useState<number | 'new' | null>(null);
  const refresh = useRefreshData();
  const navigate = useNavigate();
  const remove = useMutation({
    mutationFn: () => api.deleteEmployee(id),
    onSuccess: async () => {
      navigate('/employees');
      await refresh();
    },
  });
  if (employee.isPending) return <Loading />;
  if (employee.isError)
    return <ErrorState error={employee.error} retry={() => employee.refetch()} />;
  const person = employee.data;
  const certificateCount = person.skills.reduce(
    (total, item) => total + item.certificates.length,
    0,
  );
  return (
    <>
      {user?.role !== 'employee' && (
        <Link to="/employees" className="back-link">
          <ArrowLeft size={16} />
          {globalAccess ? 'Все сотрудники' : 'Мой отдел'}
        </Link>
      )}
      <PageHeader title={fullName(person)} description={person.position}>
        <button className="button secondary" onClick={() => setEdit(true)}>
          <Pencil size={16} />
          Редактировать
        </button>
        {globalAccess && (
          <button
            className="icon-button delete-button"
            aria-label="Удалить сотрудника"
            onClick={() => setConfirmDelete(true)}
          >
            <Trash2 size={18} />
          </button>
        )}
      </PageHeader>
      <section className="card profile-card">
        <Avatar employee={person} size="large" />
        <div className="profile-summary">
          <h2>
            {fullName(person)}
            <StatusBadge status={person.status} />
          </h2>
          <p>{person.position}</p>
          <div className="profile-details">
            <span>
              <Building2 size={16} />
              {person.department.name}
            </span>
            <a href={`mailto:${person.email}`}>
              <Mail size={16} />
              {person.email}
            </a>
            <span>
              <CalendarDays size={16} />В команде с {dateLabel(person.hired_at)}
            </span>
          </div>
        </div>
      </section>
      <section className="card resume-card">
        <div className="card-heading">
          <div>
            <h2>Резюме</h2>
            <p>Профессиональный опыт и образование</p>
          </div>
        </div>
        {[
          ['О себе', person.about],
          ['Опыт работы', person.experience],
          ['Образование', person.education],
        ].map(([title, text]) => (
          <div className="resume-section" key={title}>
            <h3>{title}</h3>
            <p className={text ? '' : 'muted'}>{text || 'Пока не заполнено'}</p>
          </div>
        ))}
      </section>
      <section className="card">
        <div className="card-heading">
          <div>
            <h2>
              Навыки и развитие<span className="count-tag">{person.skills.length}</span>
            </h2>
            <p>Текущие оценки и целевые уровни сотрудника</p>
          </div>
          <button className="button primary compact" onClick={() => setAssessment('new')}>
            <Plus size={16} />
            Добавить навык
          </button>
        </div>
        {!person.skills.length ? (
          <Empty
            title="Навыки ещё не назначены"
            description="Добавьте навыки, чтобы составить профиль компетенций."
          />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Навык</th>
                  <th>Текущий уровень</th>
                  <th>Цель</th>
                  <th>Состояние</th>
                  <th>Обновлено</th>
                  <th>Сертификаты</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {person.skills.map((item) => (
                  <tr key={item.skill.id}>
                    <td>
                      <span className="skill-table-name">
                        <BookOpen size={17} />
                        <strong>{item.skill.name}</strong>
                      </span>
                    </td>
                    <td>
                      {item.current_level === null ? (
                        <span className="muted">Не оценён</span>
                      ) : (
                        <strong>
                          {item.current_level} — {levelLabels[item.current_level]}
                        </strong>
                      )}
                    </td>
                    <td>
                      <span className="target-label">
                        <Target size={15} />
                        {item.target_level} — {levelLabels[item.target_level]}
                      </span>
                    </td>
                    <td>
                      <span className={`assessment-tag ${assessmentState(item)}`}>
                        {assessmentLabels[assessmentState(item)]}
                      </span>
                    </td>
                    <td>{timestamp(item.updated_at).toLocaleDateString('ru-RU')}</td>
                    <td>
                      <CertificateList
                        employeeId={id}
                        skillId={item.skill.id}
                        certificates={item.certificates}
                        compact
                      />
                      <button
                        className="button secondary compact"
                        aria-label={`Добавить сертификат к навыку ${item.skill.name}`}
                        onClick={() => setCertificateSkillId(item.skill.id)}
                      >
                        <Plus size={14} /> Сертификат
                      </button>
                    </td>
                    <td>
                      <button
                        className="icon-button"
                        aria-label={`Оценить ${item.skill.name}`}
                        onClick={() => setAssessment(item)}
                      >
                        <Pencil size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="overview-bottom">
          <span>Шкала 0–5 · Неоценённые навыки не входят в средний уровень</span>
          {user?.role !== 'employee' && <Link to="/matrix">Матрица команды</Link>}
        </div>
      </section>
      <section className="card" aria-label="Сертификаты сотрудника">
        <div className="card-heading">
          <div>
            <h2>
              Сертификаты<span className="count-tag">{certificateCount}</span>
            </h2>
            <p>Документы, подтверждающие навыки сотрудника</p>
          </div>
          <button
            className="button primary compact"
            disabled={!person.skills.length}
            onClick={() => setCertificateSkillId('new')}
          >
            <Plus size={16} /> Добавить сертификат
          </button>
        </div>
        {!certificateCount ? (
          <Empty
            title="Сертификатов пока нет"
            description={
              person.skills.length
                ? 'Прикрепите сертификат к одному из навыков сотрудника.'
                : 'Сначала добавьте навык, затем прикрепите к нему сертификат.'
            }
          />
        ) : (
          <div className="profile-certificates">
            {person.skills
              .filter((item) => item.certificates.length)
              .map((item) => (
                <div className="certificate-group" key={item.skill.id}>
                  <h3>{item.skill.name}</h3>
                  <CertificateList
                    employeeId={id}
                    skillId={item.skill.id}
                    certificates={item.certificates}
                  />
                </div>
              ))}
          </div>
        )}
      </section>
      {certificateSkillId !== null && (
        <CertificateForm
          employeeId={id}
          assessments={person.skills}
          initialSkillId={certificateSkillId === 'new' ? undefined : certificateSkillId}
          onClose={() => setCertificateSkillId(null)}
        />
      )}
      {edit && <EmployeeForm employee={person} onClose={() => setEdit(false)} />}
      {assessment && (
        <AssessmentForm
          employeeId={id}
          assessment={assessment === 'new' ? undefined : assessment}
          assignedIds={person.skills.map((item) => item.skill.id)}
          onClose={() => setAssessment(null)}
        />
      )}
      {confirmDelete && (
        <Modal
          title="Удалить сотрудника?"
          subtitle="Это действие нельзя отменить."
          onClose={() => {
            if (!remove.isPending) setConfirmDelete(false);
          }}
        >
          <div className="modal-form">
            <p>
              Карточка «{fullName(person)}», все её оценки навыков и файлы сертификатов будут
              удалены. Чтобы сохранить историю сотрудника, можно изменить статус на «Неактивен».
            </p>
            <FormError error={remove.error} />
            <div className="modal-actions">
              <button
                className="button secondary"
                disabled={remove.isPending}
                onClick={() => setConfirmDelete(false)}
              >
                Отмена
              </button>
              <button
                className="button danger"
                disabled={remove.isPending}
                onClick={() => remove.mutate()}
              >
                {remove.isPending ? 'Удаляем…' : 'Удалить'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
