import os
import tempfile
import zipfile
from pathlib import Path
from typing import Union
import geopandas as gpd


class GeospatialParserError(Exception):
    """Base exception for geospatial parsing errors."""

    pass


class UnsupportedFormatError(GeospatialParserError):
    """Raised when an unsupported file extension is provided."""

    pass


class InvalidFileError(GeospatialParserError):
    """Raised when a file is invalid, corrupt, missing components, or malicious."""

    pass


def parse_geospatial_file(file_path: Union[str, Path]) -> gpd.GeoDataFrame:
    r"""
    Parses a geospatial file (.kml or .zip containing a Shapefile) into a GeoPandas GeoDataFrame.

    Zip-Slip Security Protection:
    -----------------------------
    What is Zip-Slip?
    Zip-Slip is a critical security vulnerability where a crafted zip archive contains file paths
    with directory traversal characters (e.g., '../../evil.py' or '..\..\malicious.exe'). When unzipping
    without validation, files are written outside the intended destination directory, potentially
    overwriting system files or executing arbitrary code.

    How This Code Prevents Zip-Slip:
    Before extracting any file from a zip archive, we resolve the absolute path of the destination
    folder and the absolute path of each archive member. We then check that the target path is strictly
    within the temporary extraction directory boundary. If any member attempts to escape the directory,
    an `InvalidFileError` is raised immediately and extraction is aborted.

    Args:
        file_path (Union[str, Path]): Path to the .kml or .zip file on disk.

    Returns:
        gpd.GeoDataFrame: Parsed vector dataset as a GeoPandas GeoDataFrame.

    Raises:
        UnsupportedFormatError: If the file extension is not .kml or .zip.
        InvalidFileError: If the file is missing, corrupt, malicious, or lacks required components (.shp).
    """
    path = Path(file_path)

    if not path.exists():
        raise InvalidFileError(f"File not found: {file_path}")

    ext = path.suffix.lower()

    if ext == ".kml":
        return _parse_kml(path)
    elif ext == ".zip":
        return _parse_zip_shapefile(path)
    else:
        raise UnsupportedFormatError(
            f"Unsupported file format '{ext}'. Only .kml files and .zip archives containing Shapefiles are supported."
        )


def _parse_kml(kml_path: Path) -> gpd.GeoDataFrame:
    """Reads a KML file using GeoPandas pyogrio engine."""
    try:
        gdf = gpd.read_file(kml_path, engine="pyogrio", driver="KML")
    except Exception:
        try:
            gdf = gpd.read_file(kml_path, engine="pyogrio")
        except Exception as err:
            raise InvalidFileError(f"Failed to parse KML file: {str(err)}") from err

    # KML standard default CRS is WGS 84 (EPSG:4326)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    return gdf


def _parse_zip_shapefile(zip_path: Path) -> gpd.GeoDataFrame:
    """Safely unpacks a zip archive, verifies Shapefile existence, and parses it into a GeoDataFrame."""
    if not zipfile.is_zipfile(zip_path):
        raise InvalidFileError("Provided file is not a valid ZIP archive.")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir).resolve()

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Zip-slip validation check before extraction
                for member in zf.infolist():
                    target_path = (temp_dir_path / member.filename).resolve()

                    # Prevent path traversal outside temp_dir_path
                    try:
                        target_path.relative_to(temp_dir_path)
                    except ValueError:
                        raise InvalidFileError(
                            f"Security Alert: Zip-slip path traversal attempt detected in member '{member.filename}'."
                        )

                zf.extractall(temp_dir_path)
        except zipfile.BadZipFile as err:
            raise InvalidFileError(f"Corrupt or invalid ZIP archive: {str(err)}") from err

        # Search for .shp file inside extracted directory
        shp_files = list(temp_dir_path.rglob("*.shp"))
        if not shp_files:
            raise InvalidFileError(
                "No Shapefile (.shp file) found within the provided ZIP archive."
            )

        shp_path = shp_files[0]

        try:
            gdf = gpd.read_file(shp_path, engine="pyogrio")
        except Exception as err:
            raise InvalidFileError(
                f"Failed to read Shapefile from ZIP archive: {str(err)}"
            ) from err

        # Return a copy of the GeoDataFrame so data persists after temp_dir cleanup
        return gdf.copy()
