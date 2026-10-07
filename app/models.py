from sqlalchemy import Column, Integer, String
from app.database import Base


class MeasurementRecord(Base):
    __tablename__ = "measurement_records"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    feature_count = Column(Integer, nullable=False)
    crs = Column(String, nullable=True)
    status = Column(String, nullable=False, default="processed")
