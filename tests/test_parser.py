import os
import zipfile
import pytest
import geopandas as gpd
from shapely.geometry import Polygon
from app.services.parser import (
    parse_geospatial_file,
    UnsupportedFormatError,
    InvalidFileError,
)


@pytest.fixture
def sample_zip_shapefile(tmp_path):
    # Create a simple GeoDataFrame and save as shapefile in a temp dir
    poly = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
    gdf = gpd.GeoDataFrame({"id": [1], "name": ["test"]}, geometry=[poly], crs="EPSG:4326")

    shp_dir = tmp_path / "shp_src"
    shp_dir.mkdir()
    shp_file = shp_dir / "test.shp"
    gdf.to_file(shp_file, engine="pyogrio")

    # Zip the shapefile component files
    zip_path = tmp_path / "test_shapefile.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in shp_dir.iterdir():
            zf.write(f, f.name)

    return zip_path


def test_parse_valid_zip_shapefile(sample_zip_shapefile):
    gdf = parse_geospatial_file(sample_zip_shapefile)
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) == 1
    assert gdf.crs is not None


def test_unsupported_format(tmp_path):
    invalid_file = tmp_path / "data.txt"
    invalid_file.write_text("dummy text")

    with pytest.raises(UnsupportedFormatError, match="Unsupported file format"):
        parse_geospatial_file(invalid_file)


def test_zip_without_shapefile(tmp_path):
    zip_path = tmp_path / "empty_archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("readme.txt", "No shapefile here")

    with pytest.raises(InvalidFileError, match="No Shapefile .* found"):
        parse_geospatial_file(zip_path)


def test_zip_slip_prevention(tmp_path):
    zip_path = tmp_path / "malicious.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        # Include a relative path traversal in filename
        zf.writestr("../../../etc/passwd", "root:x:0:0:")

    with pytest.raises(InvalidFileError, match="Zip-slip path traversal attempt"):
        parse_geospatial_file(zip_path)
