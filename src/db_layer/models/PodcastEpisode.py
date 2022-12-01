import uuid
import enum
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.sql import functions
from sqlalchemy.orm import relationship

from .Base import Base, PostgreSQLUUID


class PodcastEpisodeStatus(str, enum.Enum):
    Inactive = "Inactive"
    Active = "Active"


class PodcastEpisode(Base):
    __tablename__ = "podcast_episode"

    id = Column(PostgreSQLUUID, primary_key=True, default=uuid.uuid4)
    title = Column(String(1024))
    link = Column(String(1024))
    status = Column(String(500))
    published_date = Column(DateTime(timezone=True))
    external_id = Column(String(500))
    episode_number = Column(Integer())
    episode_duration = Column(String(100))
    podcast_id = Column(PostgreSQLUUID, ForeignKey("podcast.id"), nullable=False)
    podcast = relationship("Podcast", back_populates="podcast_episodes")
    created_at = Column(DateTime(timezone=True), server_default=functions.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=functions.now(),
        onupdate=functions.now(),
    )

    def __init__(
        self,
        title: str,
        link: str,
        published_date: str,
        external_id: str,
        episode_number: int,
        episode_duration: str,
        podcast_id: uuid.UUID,
        status: str = PodcastEpisodeStatus.Active,
    ):
        self.title = title
        self.link = link
        self.status = status
        self.published_date = published_date
        self.external_id = external_id
        self.episode_number = episode_number
        self.episode_duration = episode_duration
        self.podcast_id = podcast_id

    def __repr__(self) -> str:
        return self.title
