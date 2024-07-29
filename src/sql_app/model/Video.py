from sqlalchemy import Column, Integer, String, Text, Boolean

from ..db import Base


class Video(Base):
    __tablename__ = 'video'
    id = Column(Integer, primary_key=True)
    title = Column(String(128))
    description = Column(Text)
    yt_link = Column(String(128), unique=True)
    thumbnail_url = Column(String(128))
    author_id = Column(String(16))
    is_reviewed = Column(Boolean, default=None, nullable=True)
    is_complete = Column(Boolean, default=False)


