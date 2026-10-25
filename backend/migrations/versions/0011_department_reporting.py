"""Keep reporting inside departments and derive manager status from actual reports."""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text("""
        UPDATE employees SET manager_id = NULL
        WHERE EXISTS (
            SELECT 1 FROM employees AS manager
            WHERE manager.id = employees.manager_id
              AND manager.department_id != employees.department_id
        )
    """)
    )
    op.execute(
        sa.text("""
        UPDATE employees SET is_manager = EXISTS (
            SELECT 1 FROM employees AS report
            WHERE report.manager_id = employees.id
              AND report.department_id = employees.department_id
        )
    """)
    )
    op.execute(
        sa.text("""
        DELETE FROM auth_sessions WHERE account_id IN (
            SELECT accounts.id FROM accounts JOIN employees ON employees.id = accounts.employee_id
            WHERE accounts.role IN ('employee', 'manager')
              AND accounts.role != CASE WHEN employees.is_manager THEN 'manager' ELSE 'employee' END
        )
    """)
    )
    op.execute(
        sa.text("""
        UPDATE accounts SET role = (
            SELECT CASE WHEN employees.is_manager THEN 'manager' ELSE 'employee' END
            FROM employees WHERE employees.id = accounts.employee_id
        )
        WHERE role IN ('employee', 'manager')
    """)
    )


def downgrade():
    # The previous schema supports these relationships. Do not restore invalid access or links.
    pass
