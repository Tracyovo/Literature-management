from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from .database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    literatures = relationship("Literature", back_populates="category")


class Literature(Base):
    __tablename__ = "literatures"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    authors = Column(String(255), nullable=True)
    year = Column(Integer, nullable=True)
    journal = Column(String(255), nullable=True)
    abstract = Column(Text, nullable=True)
    citation = Column(Text, nullable=True)
    file_path = Column(String(512), nullable=True)
    file_name = Column(String(255), nullable=True)
    content_text = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    category = relationship("Category", back_populates="literatures")
