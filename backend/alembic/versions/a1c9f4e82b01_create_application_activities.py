"""Create application_activities table for application history."""

from alembic import op
import sqlalchemy as sa


revision = "a1c9f4e82b01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "application_activities" in inspector.get_table_names():
        return

    op.create_table(
        "application_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey("job_applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("old_value", sa.String(length=255), nullable=True),
        sa.Column("new_value", sa.String(length=255), nullable=True),
        sa.Column(
            "event_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_application_activities_id", "application_activities", ["id"])
    op.create_index(
        "ix_application_activities_application_id",
        "application_activities",
        ["application_id"],
    )
    op.create_index(
        "ix_application_activities_event_at",
        "application_activities",
        ["event_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_application_activities_event_at", table_name="application_activities")
    op.drop_index(
        "ix_application_activities_application_id",
        table_name="application_activities",
    )
    op.drop_index("ix_application_activities_id", table_name="application_activities")
    op.drop_table("application_activities")

