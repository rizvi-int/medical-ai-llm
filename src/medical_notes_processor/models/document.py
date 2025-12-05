from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from ..db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    patient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    encounter_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}')>"
