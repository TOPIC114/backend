# class Video(Base):
#     __tablename__ = 'video'
#     id = Column(Integer, primary_key=True)
#     title = Column(String(128))
#     description = Column(Text)
#     yt_link = Column(String(128), unique=True)
#     thumbnail_url = Column(String(128))
#     author_id = Column(String(16))
#     is_download = Column(Boolean)
#     is_complete = Column(Boolean, default=False)
from pydantic import BaseModel


class VideoRequest(BaseModel):
    title: str
    description: str
    yt_link: str
    thumbnail_url: str
    author_id: str
