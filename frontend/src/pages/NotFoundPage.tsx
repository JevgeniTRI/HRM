import { Link } from 'react-router-dom';
import { Empty } from '../components/ui';

export function NotFoundPage() {
  return (
    <section className="card">
      <Empty title="Страница не найдена" description="Проверьте адрес или вернитесь на главную.">
        <Link to="/" className="button primary">
          На главную
        </Link>
      </Empty>
    </section>
  );
}
