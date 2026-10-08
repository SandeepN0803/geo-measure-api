import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import UploadedFile, Feature
from app.schemas import FileInfoResponse, FeatureResponse, MeasurementsListResponse


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_models_and_relationship(db_session):
    # Create an UploadedFile
    uploaded_file = UploadedFile(
        filename="test.kml",
        status="COMPLETED",
        feature_count=1,
        crs="EPSG:4326"
    )
    db_session.add(uploaded_file)
    db_session.commit()
    db_session.refresh(uploaded_file)

    assert uploaded_file.id is not None

    # Create a Feature linked to uploaded_file
    feature = Feature(
        file_id=uploaded_file.id,
        feature_index=0,
        geometry_type="Polygon",
        geometry={"type": "Polygon", "coordinates": []},
        properties={"name": "test_area"},
        measurement_type="area",
        measurement_value=123.45,
        unit="square_meters",
        crs_used="EPSG:32633",
        note=None
    )
    db_session.add(feature)
    db_session.commit()

    # Query and check relationship
    file_record = db_session.query(UploadedFile).filter_by(id=uploaded_file.id).first()
    assert len(file_record.features) == 1
    assert file_record.features[0].measurement_value == 123.45


def test_pydantic_schemas():
    file_info = FileInfoResponse(
        id="test-uuid-123",
        filename="sample.zip",
        feature_count=2,
        crs="EPSG:4326",
        status="COMPLETED"
    )
    assert file_info.id == "test-uuid-123"

    feat = FeatureResponse(
        feature_index=0,
        geometry_type="LineString",
        measurement_type="length",
        measurement_value=50.0,
        unit="meters"
    )
    assert feat.measurement_value == 50.0

    measurements_list = MeasurementsListResponse(file=file_info, features=[feat])
    assert len(measurements_list.features) == 1
