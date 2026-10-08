from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Setup isolated in-memory test database with StaticPool to persist tables across session connections
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine_test = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

DATA_DIR = Path(__file__).parent / "data"
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Fixture that creates clean in-memory tables before each test and drops them afterwards."""
    Base.metadata.create_all(bind=engine_test)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine_test)


def test_upload_valid_kml():
    """Uploads a valid KML file and verifies successful response and feature count."""
    kml_path = DATA_DIR / "sample.kml"
    with open(kml_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample.kml", f.read(), "application/vnd.google-earth.kml+xml")},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "sample.kml"
    assert data["status"] == "COMPLETED"
    assert data["feature_count"] == 3


def test_upload_valid_zipped_shapefile():
    """Uploads a valid zipped Shapefile and verifies database persistence and processing status."""
    zip_path = DATA_DIR / "sample_shapefile.zip"
    with open(zip_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_shapefile.zip", f.read(), "application/zip")},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "sample_shapefile.zip"
    assert data["status"] == "COMPLETED"
    assert data["feature_count"] >= 1


def test_wrong_file_extension_returns_400():
    """Verifies that uploading a file with an unaccepted extension returns HTTP 400 Bad Request."""
    response = client.post(
        "/api/files/",
        files={"file": ("document.txt", b"plain text data", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_corrupt_kml_returns_400():
    """Verifies that uploading malformed/corrupt KML XML returns HTTP 400 Bad Request."""
    corrupt_path = DATA_DIR / "corrupt.kml"
    with open(corrupt_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("corrupt.kml", f.read(), "application/vnd.google-earth.kml+xml")},
        )
    assert response.status_code == 400
    assert "detail" in response.json()


def test_bad_zip_without_shp_returns_400():
    """Verifies that uploading a zip file lacking a .shp file returns HTTP 400 Bad Request."""
    bad_zip_path = DATA_DIR / "bad.zip"
    with open(bad_zip_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("bad.zip", f.read(), "application/zip")},
        )
    assert response.status_code == 400
    assert "No Shapefile" in response.json()["detail"]


def test_unknown_file_id_returns_404():
    """Verifies querying metadata or measurements for a non-existent file ID returns HTTP 404 Not Found."""
    info_resp = client.get("/api/files/non-existent-uuid/")
    assert info_resp.status_code == 404
    assert "was not found" in info_resp.json()["detail"]

    meas_resp = client.get("/api/files/non-existent-uuid/measurements/")
    assert meas_resp.status_code == 404
    assert "was not found" in meas_resp.json()["detail"]


def test_polygon_area_accuracy_with_tolerance():
    """Verifies that polygon area is calculated in meters (~1,000,000 m²) within a reasonable tolerance."""
    kml_path = DATA_DIR / "sample.kml"
    with open(kml_path, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("sample.kml", f.read(), "application/vnd.google-earth.kml+xml")},
        )
    file_id = upload_resp.json()["id"]

    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    features = meas_resp.json()["features"]

    poly_feature = next(f for f in features if f["geometry_type"] == "Polygon")
    assert poly_feature["measurement_type"] == "area"
    assert poly_feature["unit"] == "square_meters"

    # Expected ~1,000,000 m², checking within +-15,000 m² (1.5%) tolerance for UTM reprojection
    assert poly_feature["measurement_value"] == pytest.approx(1_000_000, abs=15_000)


def test_point_has_no_measurement():
    """Verifies that Point geometries return no measurement value, unit, or measurement type."""
    kml_path = DATA_DIR / "sample.kml"
    with open(kml_path, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("sample.kml", f.read(), "application/vnd.google-earth.kml+xml")},
        )
    file_id = upload_resp.json()["id"]

    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    features = meas_resp.json()["features"]

    point_feature = next(f for f in features if f["geometry_type"] == "Point")
    assert point_feature["measurement_type"] is None
    assert point_feature["measurement_value"] is None
    assert point_feature["unit"] is None
    assert point_feature["note"] is not None
    assert "Point geometry" in point_feature["note"]


def test_unsupported_geometry_does_not_crash_request():
    """Verifies that datasets with points or unsupported geometries complete HTTP 201 without crashing or returning HTTP 500."""
    kml_path = DATA_DIR / "sample.kml"
    with open(kml_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample.kml", f.read(), "application/vnd.google-earth.kml+xml")},
        )
    assert response.status_code == 201
    assert response.json()["status"] == "COMPLETED"
