"""Init schema

Revision ID: 0d6213bec915
Revises: 
Create Date: 2022-12-01 22:25:50.628614

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0d6213bec915"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "podcast",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collection_id", sa.String(length=100), nullable=False),
        sa.Column("track_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("feed_url", sa.String(length=500), nullable=False),
        sa.Column("genre_ids", sa.String(length=500), nullable=True),
        sa.Column("genre_names", sa.String(length=1000), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "podcast_episode",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("link", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=500), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_id", sa.String(length=500), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("episode_duration", sa.String(length=100), nullable=True),
        sa.Column("podcast_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["podcast_id"],
            ["podcast.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("podcast_episode")
    op.drop_table("podcast")
    # ### end Alembic commands ###
