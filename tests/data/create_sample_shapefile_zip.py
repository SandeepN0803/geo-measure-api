import os
import tempfile
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon, LineString

def generate_shapefile_zip(output_zip_path: str):
    """
    Generates a zipped Shapefile archive containing a polygon shapefile and a line shapefile.
    """
    poly = Polygon([
        (77.590000, 12.970000),
        (77.599218, 12.970000),
        (77.599218, 12.978983),
        (77.590000, 12.978983),
        (77.590000, 12.970000)
    ])
    line = LineString([
        (77.590000, 12.970000),
        (77.599218, 12.970000)
    ])

    gdf_poly = gpd.GeoDataFrame(
        {"name": ["Bengaluru Polygon"], "type": ["Polygon"]},
        geometry=[poly],
        crs="EPSG:4326"
    )

    gdf_line = gpd.GeoDataFrame(
        {"name": ["Bengaluru Line"], "type": ["LineString"]},
        geometry=[line],
        crs="EPSG:4326"
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        poly_shp = os.path.join(tmp_dir, "polygon_features.shp")
        line_shp = os.path.join(tmp_dir, "line_features.shp")

        gdf_poly.to_file(poly_shp, engine="pyogrio")
        gdf_line.to_file(line_shp, engine="pyogrio")

        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in os.listdir(tmp_dir):
                full_path = os.path.join(tmp_dir, f)
                zf.write(full_path, arcname=f)

if __name__ == "__main__":
    target_path = os.path.join(os.path.dirname(__file__), "sample_shapefile.zip")
    generate_shapefile_zip(target_path)
    print(f"Successfully generated zipped Shapefile at: {target_path}")
