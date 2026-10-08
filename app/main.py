import logging
import os
import tempfile
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db
from app.schemas import (
    FeatureResponse,
    FileInfoResponse,
    HealthResponse,
    MeasurementsListResponse,
)
from app.services.measure import calculate_measurements
from app.services.parser import (
    GeospatialParserError,
    InvalidFileError,
    UnsupportedFormatError,
    parse_geospatial_file,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("geo_measure_api")

# Create database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="geo-measure-api",
    description="API for extracting features and calculating area/length measurements from geospatial files (.kml, .zip Shapefiles).",
    version="0.1.0",
)

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent unhandled 500 stack trace leaks."""
    logger.error(f"Unhandled internal server error at {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred while processing your request."},
    )


@app.get("/", tags=["Health"])
def root_welcome():
    """Welcome endpoint pointing users to interactive documentation."""
    return {
        "message": "Welcome to geo-measure-api!",
        "docs_url": "http://127.0.0.1:8000/docs",
        "health_url": "http://127.0.0.1:8000/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Health check endpoint to verify backend service status."""
    return HealthResponse(status="ok", message="geo-measure-api is healthy")


@app.post(
    "/api/files/",
    response_model=FileInfoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Files"],
    summary="Upload and process a geospatial file (.kml or Shapefile .zip)",
)
async def upload_file(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    filename = file.filename or "uploaded_file"
    ext = Path(filename).suffix.lower()

    # 1. Validate file extension
    if ext not in (".kml", ".zip"):
        logger.warning(f"Rejected upload with unsupported extension '{ext}': {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only .kml files and .zip archives containing Shapefiles are accepted.",
        )

    # 2. Read and validate max file size (20 MB)
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        logger.warning(
            f"Rejected upload exceeding 20 MB limit ({len(contents)} bytes): {filename}"
        )
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size exceeds the maximum allowed limit of 20 MB.",
        )

    # 3. Save bytes to a temporary file for parsing
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        logger.info(f"Parsing uploaded geospatial file: {filename}")
        gdf = parse_geospatial_file(tmp_path)
        crs_str = str(gdf.crs) if gdf.crs else "EPSG:4326"

        logger.info(
            f"Calculating measurements for {len(gdf)} features in file: {filename}"
        )
        measurements = calculate_measurements(gdf, default_crs="EPSG:4326")

        # 4. Save file metadata to database
        db_file = models.UploadedFile(
            filename=filename,
            status="COMPLETED",
            feature_count=len(gdf),
            crs=crs_str,
            error_message=None,
        )
        db.add(db_file)
        db.flush()  # Populates db_file.id

        # 5. Save feature records to database
        for item in measurements:
            db_feature = models.Feature(
                file_id=db_file.id,
                feature_index=item["index"],
                geometry_type=item["geometry_type"],
                geometry=item["geometry"],
                properties=item["properties"],
                measurement_type=item["measurement_type"],
                measurement_value=item["measurement_value"],
                unit=item["unit"],
                crs_used=item["crs_used"],
                note=item["note"],
            )
            db.add(db_feature)

        db.commit()
        db.refresh(db_file)
        logger.info(
            f"Successfully processed file '{filename}' with generated ID: {db_file.id}"
        )
        return db_file

    except (GeospatialParserError, ValueError) as err:
        logger.warning(f"Validation or parsing failed for '{filename}': {err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get(
    "/api/files/{id}/",
    response_model=FileInfoResponse,
    tags=["Files"],
    summary="Get file metadata by ID",
)
def get_file_info(id: str, db: Session = Depends(get_db)):
    db_file = db.query(models.UploadedFile).filter(models.UploadedFile.id == id).first()
    if not db_file:
        logger.warning(f"File metadata request for non-existent ID: {id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' was not found.",
        )
    return db_file


@app.get(
    "/api/files/{id}/measurements/",
    response_model=MeasurementsListResponse,
    tags=["Files"],
    summary="Get feature measurements for a specific file ID",
)
def get_file_measurements(id: str, db: Session = Depends(get_db)):
    db_file = db.query(models.UploadedFile).filter(models.UploadedFile.id == id).first()
    if not db_file:
        logger.warning(f"File measurements request for non-existent ID: {id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' was not found.",
        )

    return MeasurementsListResponse(
        file=FileInfoResponse.model_validate(db_file),
        features=[FeatureResponse.model_validate(f) for f in db_file.features],
    )
