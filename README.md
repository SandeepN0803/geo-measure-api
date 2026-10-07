# geo-measure-api

FastAPI backend for accepting geospatial files (`.kml` or `.zip` containing Shapefiles), extracting features, and calculating area and length measurements.

## Features
- Upload `.kml` or `.zip` Shapefile archives
- Extract vector geometries
- Compute surface area (m²) and length/perimeter (m) using reprojected CRS
- SQLite persistence with SQLAlchemy

## Setup

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Unix:
source venv/bin/activate

pip install -r requirements.txt
```

## Running the API

```bash
uvicorn app.main:app --reload
```

## Running Tests

```bash
pytest
```
