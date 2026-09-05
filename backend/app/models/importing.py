from __future__ import annotations

import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class DataImportJob(Base, TimestampMixin):
    """Tracks one file-import workflow end to end: upload -> column mapping
    -> validation -> preview -> commit -> report. Nothing is written to
    business tables until status reaches VALIDATED and the user explicitly
    confirms the commit step."""

    __tablename__ = "data_import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(30), nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UPLOADED", index=True)
    column_mapping: Mapped[dict | None] = mapped_column(JSON)
    total_rows: Mapped[int | None] = mapped_column(Integer)
    valid_rows: Mapped[int | None] = mapped_column(Integer)
    invalid_rows: Mapped[int | None] = mapped_column(Integer)
    duplicate_rows: Mapped[int | None] = mapped_column(Integer)
    error_report: Mapped[dict | None] = mapped_column(JSON)
    raw_rows_cache: Mapped[dict | None] = mapped_column(JSON)
    committed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
