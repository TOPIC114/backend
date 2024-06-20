from ..db import Base
from sqlalchemy import Column, Integer, String, TEXT, DateTime


class Model(Base):
    __tablename__ = 'model'
    id = Column(Integer, primary_key=True)
    file_path = Column(String(60), nullable=False)
    description = Column(TEXT, nullable=False)
    size = Column(String(30), nullable=False)
    version = Column(String(30), nullable=False)
    update_date = Column(DateTime, nullable=False)
