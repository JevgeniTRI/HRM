import { BookOpen, Building2, Check, ChevronRight, Clock3, Columns3, UserPlus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Activity } from '../../types';
import { activityTime } from '../../lib/format';
import { Empty } from '../ui';

const eventIcons: Record<string, LucideIcon> = {
  assessment: Check,
  department: Building2,
  skill: BookOpen,
  task: Columns3,
};

export function ActivityFeed({ activities }: { activities: Activity[] }) {
  return (
    <section className="card activity-card">
      <div className="card-heading">
        <div>
          <h2>Последние события</h2>
          <p>Что нового в вашей команде</p>
        </div>
        <span className="subtle-icon">
          <Clock3 size={19} />
        </span>
      </div>
      <div className="activity-list">
        {!activities.length ? (
          <Empty
            title="История пока пуста"
            description="Здесь появятся изменения сотрудников и навыков."
          />
        ) : (
          activities.map((activity) => {
            const Icon = eventIcons[activity.kind] ?? UserPlus;
            const content = (
              <>
                <span
                  className={`event-icon ${activity.kind === 'assessment' ? 'green' : 'lilac'}`}
                >
                  <Icon size={17} />
                </span>
                <div className="activity-text">
                  <strong>{activity.title}</strong>
                  <p>{activity.detail}</p>
                  <small>{activity.actor_username}</small>
                </div>
                <time>{activityTime(activity.created_at)}</time>
                {activity.employee_id && <ChevronRight className="event-chevron" size={14} />}
              </>
            );
            return activity.employee_id ? (
              <Link
                to={`/employees/${activity.employee_id}`}
                className="activity-row"
                key={activity.id}
              >
                {content}
              </Link>
            ) : (
              <div className="activity-row" key={activity.id}>
                {content}
              </div>
            );
          })
        )}
      </div>
      <div className="activity-footer">
        <span className="live-dot" />
        История обновляется после изменений
      </div>
    </section>
  );
}
