import pytest
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point, GeometryCollection
from app.services.measure import calculate_measurements


def test_polygon_area_measurement():
    poly = Polygon([(0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0), (0, 0)])
    gdf = gpd.GeoDataFrame({"name": ["square_poly"]}, geometry=[poly], crs="EPSG:4326")

    results = calculate_measurements(gdf)
    assert len(results) == 1
    res = results[0]
    assert res["geometry_type"] == "Polygon"
    assert res["measurement_type"] == "area"
    assert res["unit"] == "square_meters"
    assert res["measurement_value"] > 0
    assert res["status"] == "success"
    assert "UTM" in res["crs_used"] or "EPSG" in res["crs_used"]


def test_linestring_length_measurement():
    line = LineString([(0, 0), (0.01, 0.01)])
    gdf = gpd.GeoDataFrame({"name": ["sample_line"]}, geometry=[line], crs="EPSG:4326")

    results = calculate_measurements(gdf)
    assert len(results) == 1
    res = results[0]
    assert res["geometry_type"] == "LineString"
    assert res["measurement_type"] == "length"
    assert res["unit"] == "meters"
    assert res["measurement_value"] > 0
    assert res["status"] == "success"


def test_point_no_measurement():
    point = Point(0, 0)
    gdf = gpd.GeoDataFrame({"name": ["origin"]}, geometry=[point], crs="EPSG:4326")

    results = calculate_measurements(gdf)
    assert len(results) == 1
    res = results[0]
    assert res["geometry_type"] == "Point"
    assert res["measurement_type"] is None
    assert res["measurement_value"] is None
    assert res["unit"] is None
    assert res["status"] == "unsupported"
    assert "Point geometry" in res["note"]


def test_missing_crs_handling():
    poly = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
    gdf = gpd.GeoDataFrame({"name": ["nocrs"]}, geometry=[poly])

    # Should raise ValueError if no default_crs is specified
    with pytest.raises(ValueError, match="GeoDataFrame missing CRS metadata"):
        calculate_measurements(gdf)

    # Should succeed when default_crs is specified
    results = calculate_measurements(gdf, default_crs="EPSG:4326")
    assert len(results) == 1
    assert results[0]["status"] == "success"


def test_empty_geometry_handling():
    gdf = gpd.GeoDataFrame({"name": ["empty"]}, geometry=[Polygon()], crs="EPSG:4326")

    results = calculate_measurements(gdf)
    assert len(results) == 1
    res = results[0]
    assert res["status"] == "unsupported"
    assert "missing or empty" in res["note"]
