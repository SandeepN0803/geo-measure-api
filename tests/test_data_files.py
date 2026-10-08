from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.parser import parse_geospatial_file, InvalidFileError

client = TestClient(app)
DATA_DIR = Path(__file__).parent / "data"


def test_sample_kml_api():
    sample_kml_path = DATA_DIR / "sample.kml"
    with open(sample_kml_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample.kml", f.read(), "application/vnd.google-earth.kml+xml")}
        )

    assert response.status_code == 201
    file_id = response.json()["id"]

    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    features = meas_resp.json()["features"]
    assert len(features) == 3

    # Polygon check
    poly_feat = features[0]
    assert poly_feat["geometry_type"] == "Polygon"
    assert poly_feat["measurement_type"] == "area"
    assert pytest.approx(poly_feat["measurement_value"], abs=10000) == 995059.3

    # Line check
    line_feat = features[1]
    assert line_feat["geometry_type"] == "LineString"
    assert line_feat["measurement_type"] == "length"
    assert pytest.approx(line_feat["measurement_value"], abs=10) == 1000.7

    # Point check
    point_feat = features[2]
    assert point_feat["geometry_type"] == "Point"
    assert point_feat["measurement_type"] is None
    assert point_feat["measurement_value"] is None


def test_sample_shapefile_zip_api():
    zip_path = DATA_DIR / "sample_shapefile.zip"
    with open(zip_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_shapefile.zip", f.read(), "application/zip")}
        )
    assert response.status_code == 201
    file_id = response.json()["id"]

    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    features = meas_resp.json()["features"]
    assert len(features) >= 1


def test_corrupt_kml_api():
    corrupt_path = DATA_DIR / "corrupt.kml"
    with open(corrupt_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("corrupt.kml", f.read(), "application/vnd.google-earth.kml+xml")}
        )
    assert response.status_code == 400


def test_bad_zip_api():
    bad_zip_path = DATA_DIR / "bad.zip"
    with open(bad_zip_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("bad.zip", f.read(), "application/zip")}
        )
    assert response.status_code == 400
