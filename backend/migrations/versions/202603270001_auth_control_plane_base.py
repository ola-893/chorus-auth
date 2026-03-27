"""Create auth control plane base schema."""

from alembic import op

from src.db.base import Base
from src.db import models  # noqa: F401


revision = "202603270001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
