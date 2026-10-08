import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship
from app.database import Base


class UploadedFile(Base):
    """
    Represents an uploaded geospatial file (.kml or Shapefile zip).

    Table Relationship:
    - One `UploadedFile` has many `Feature` items (One-to-Many).
    - Foreign Key: `Feature.file_id` references `uploaded_files.id`.
    - Deleting an `UploadedFile` automatically deletes its associated `Feature` records via cascade.
    """

    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PROCESSING")  # PROCESSING, COMPLETED, FAILED
    feature_count = Column(Integer, nullable=False, default=0)
    crs = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    features = relationship(
        "Feature", back_populates="file", cascade="all, delete-orphan"
    )


class Feature(Base):
    """
    Represents an individual spatial feature extracted from an UploadedFile.
    """

    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_id = Column(
        String, ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False
    )
    feature_index = Column(Integer, nullable=False)
    geometry_type = Column(String, nullable=True)
    geometry = Column(JSON, nullable=True)
    properties = Column(JSON, nullable=True)
    measurement_type = Column(String, nullable=True)  # area, length, or None
    measurement_value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)  # square_meters, meters, or None
    crs_used = Column(String, nullable=True)
    note = Column(String, nullable=True)

    file = relationship("UploadedFile", back_populates="features")
