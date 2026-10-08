from typing import Any, Dict, List, Optional
import geopandas as gpd
from shapely.geometry import mapping


def calculate_measurements(
    gdf: gpd.GeoDataFrame, default_crs: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Calculates spatial measurements (area in square meters or length in meters)
    for each feature in a GeoPandas GeoDataFrame.

    CRS Handling Explained Simply:
    ------------------------------
    1. Geographic vs. Projected CRS:
       Latitude and longitude coordinates (such as EPSG:4326 used in KML files) are measured
       in angular degrees on a sphere. Calculating area or distance using degree coordinates
       gives meaningless results (e.g., square degrees).
    2. Missing CRS Fallback:
       If the input dataset has no defined CRS, you must supply `default_crs` (e.g., 'EPSG:4326').
       If no CRS is present and no default is provided, a ValueError is raised.
    3. UTM Reprojection for Accurate Metric Calculations:
       Before performing any calculations, each geometry is dynamically reprojected to its local
       UTM (Universal Transverse Mercator) zone using GeoPandas' `estimate_utm_crs()`. UTM zones
       project the 3D surface of the Earth onto 2D metric grids (meters), allowing accurate
       surface area (m²) and linear length (m) calculations.

    Args:
        gdf (gpd.GeoDataFrame): GeoDataFrame containing features to measure.
        default_crs (Optional[str]): Fallback CRS string (e.g. 'EPSG:4326') if gdf.crs is missing.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, one per feature, containing geometry details,
                              properties, measurement results, CRS used, and status/notes.

    Raises:
        ValueError: If `gdf.crs` is missing and no `default_crs` is specified.
    """
    if gdf.crs is None:
        if default_crs:
            gdf = gdf.set_crs(default_crs)
        else:
            raise ValueError(
                "GeoDataFrame missing CRS metadata. Provide a valid CRS or specify default_crs (e.g., 'EPSG:4326')."
            )

    original_crs_str = str(gdf.crs)
    geom_col = gdf.active_geometry_name

    results: List[Dict[str, Any]] = []

    for idx, row in gdf.iterrows():
        raw_geom = row.get(geom_col)

        # Extract non-geometry attributes as properties
        properties = {}
        for col_name, val in row.items():
            if col_name == geom_col:
                continue
            if hasattr(val, "item"):
                val = val.item()
            elif isinstance(val, (float, int, str, bool, type(None))):
                pass
            else:
                val = str(val)
            properties[col_name] = val

        # Handle missing or empty geometries
        if raw_geom is None or raw_geom.is_empty:
            results.append(
                {
                    "index": idx,
                    "geometry_type": None,
                    "geometry": None,
                    "original_crs": original_crs_str,
                    "properties": properties,
                    "measurement_type": None,
                    "measurement_value": None,
                    "unit": None,
                    "crs_used": None,
                    "status": "unsupported",
                    "note": "Geometry is missing or empty.",
                }
            )
            continue

        geom_type = raw_geom.geom_type
        geojson_geom = mapping(raw_geom)

        # Handle invalid geometries safely without crashing
        if not raw_geom.is_valid:
            results.append(
                {
                    "index": idx,
                    "geometry_type": geom_type,
                    "geometry": geojson_geom,
                    "original_crs": original_crs_str,
                    "properties": properties,
                    "measurement_type": None,
                    "measurement_value": None,
                    "unit": None,
                    "crs_used": None,
                    "status": "unsupported",
                    "note": f"Invalid geometry at index {idx}.",
                }
            )
            continue

        # Determine measurement type based on geometry classification
        if geom_type in ("Polygon", "MultiPolygon"):
            meas_type = "area"
            unit = "square_meters"
        elif geom_type in ("LineString", "MultiLineString"):
            meas_type = "length"
            unit = "meters"
        elif geom_type in ("Point", "MultiPoint"):
            results.append(
                {
                    "index": idx,
                    "geometry_type": geom_type,
                    "geometry": geojson_geom,
                    "original_crs": original_crs_str,
                    "properties": properties,
                    "measurement_type": None,
                    "measurement_value": None,
                    "unit": None,
                    "crs_used": None,
                    "status": "unsupported",
                    "note": "Point geometry has no area or length measurement.",
                }
            )
            continue
        else:
            results.append(
                {
                    "index": idx,
                    "geometry_type": geom_type,
                    "geometry": geojson_geom,
                    "original_crs": original_crs_str,
                    "properties": properties,
                    "measurement_type": None,
                    "measurement_value": None,
                    "unit": None,
                    "crs_used": None,
                    "status": "unsupported",
                    "note": f"Unsupported geometry type: '{geom_type}'.",
                }
            )
            continue

        # Reproject geometry to local UTM projected CRS for metric calculation
        try:
            feature_series = gpd.GeoSeries([raw_geom], crs=gdf.crs)
            utm_crs = feature_series.estimate_utm_crs()
            reprojected_series = feature_series.to_crs(utm_crs)
            reprojected_geom = reprojected_series.iloc[0]
            crs_used_str = str(utm_crs)

            if meas_type == "area":
                val = float(reprojected_geom.area)
            else:
                val = float(reprojected_geom.length)

            results.append(
                {
                    "index": idx,
                    "geometry_type": geom_type,
                    "geometry": geojson_geom,
                    "original_crs": original_crs_str,
                    "properties": properties,
                    "measurement_type": meas_type,
                    "measurement_value": val,
                    "unit": unit,
                    "crs_used": crs_used_str,
                    "status": "success",
                    "note": None,
                }
            )
        except Exception as err:
            results.append(
                {
                    "index": idx,
                    "geometry_type": geom_type,
                    "geometry": geojson_geom,
                    "original_crs": original_crs_str,
                    "properties": properties,
                    "measurement_type": meas_type,
                    "measurement_value": None,
                    "unit": unit,
                    "crs_used": None,
                    "status": "unsupported",
                    "note": f"Error estimating UTM CRS: {str(err)}",
                }
            )

    return results
