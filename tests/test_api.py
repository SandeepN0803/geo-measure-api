import io
import zipfile
import pytest
from fastapi.testclient import TestClient
import geopandas as gpd
from shapely.geometry import Polygon
from app.main import app

client = TestClient(app)


@pytest.fixture
def create_sample_zip():
    poly = Polygon([(0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0), (0, 0)])
    gdf = gpd.GeoDataFrame({"id": [101], "name": ["test_zone"]}, geometry=[poly], crs="EPSG:4326")

    # Save shapefile in memory zip
    zip_bytes_io = io.BytesIO()
    with zipfile.ZipFile(zip_bytes_io, "w") as zf:
        with tempfile_dir() as tmp_dir:
            shp_path = os.path.join(tmp_dir, "test.shp")
            gdf.to_file(shp_path, engine="pyogrio")
            for f in os.listdir(tmp_dir):
                full_f = os.path.join(tmp_dir, f)
                with open(full_f, "rb") as fp:
                    zf.writestr(f, fp.read())

    zip_bytes_io.seek(0)
    return zip_bytes_io.read()


import os
import tempfile
from contextlib import contextmanager

@contextmanager
def tempfile_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


def test_upload_and_retrieve_file(create_sample_zip):
    # 1. Upload valid shapefile zip
    response = client.post(
        "/api/files/",
        files={"file": ("test_shapefile.zip", create_sample_zip, "application/zip")}
    )
    assert response.status_code == 201
    file_data = response.json()
    assert file_data["filename"] == "test_shapefile.zip"
    assert file_data["status"] == "COMPLETED"
    assert file_data["feature_count"] == 1
    file_id = file_data["id"]

    # 2. Get file info
    info_resp = client.get(f"/api/files/{file_id}/")
    assert info_resp.status_code == 200
    assert info_resp.json()["id"] == file_id

    # 3. Get measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert meas_data["file"]["id"] == file_id
    assert len(meas_data["features"]) == 1
    feat = meas_data["features"][0]
    assert feat["geometry_type"] == "Polygon"
    assert feat["measurement_type"] == "area"
    assert feat["unit"] == "square_meters"
    assert feat["measurement_value"] > 0


def test_upload_invalid_extension():
    response = client.post(
        "/api/files/",
        files={"file": ("invalid.txt", b"some text content", "text/plain")}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_too_large_file():
    large_content = b"0" * (20 * 1024 * 1024 + 1)  # > 20 MB
    response = client.post(
        "/api/files/",
        files={"file": ("large_file.zip", large_content, "application/zip")}
    )
    assert response.status_code == 413
    assert "File size exceeds" in response.json()["detail"]


def test_get_nonexistent_file():
    response = client.get("/api/files/non-existent-uuid/")
    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


def test_get_nonexistent_file_measurements():
    response = client.get("/api/files/non-existent-uuid/measurements/")
    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]
