import uuid
import enum
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import functions
from sqlalchemy.orm import relationship

from .Base import Base, PostgreSQLUUID


class PodcastStatus(str, enum.Enum):
    Inactive = "Inactive"
    Active = "Active"
    Init = "Init"


class Podcast(Base):
    __tablename__ = "podcast"

    id = Column(PostgreSQLUUID, primary_key=True, default=uuid.uuid4)
    collection_id = Column(String(100), nullable=False)
    track_id = Column(String(100), nullable=False)
    name = Column(String(512))
    feed_url = Column(String(500), nullable=False)
    genre_ids = Column(String(500))
    genre_names = Column(String(1000))
    published_date = Column(DateTime(timezone=True))
    podcast_episodes = relationship("PodcastEpisode", back_populates="podcast")
    status = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=functions.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=functions.now(),
        onupdate=functions.now(),
    )

    def __init__(
        self,
        collection_id: str,
        track_id: str,
        feed_url: str,
        name: Optional[str] = None,
        genre_ids: Optional[str] = None,
        genre_names: Optional[str] = None,
        published_date: datetime = None,
        status: str = PodcastStatus.Init,
    ):
        self.collection_id = collection_id
        self.track_id = track_id
        self.feed_url = feed_url
        self.genre_ids = genre_ids
        self.genre_names = genre_names
        self.published_date = published_date
        self.status = status
        self.name = name

    def __repr__(self) -> str:
        return self.name
