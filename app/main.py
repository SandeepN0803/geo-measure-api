from fastapi import FastAPI
from app.database import Base, engine
from app import models  # noqa: F401
from app.schemas import HealthResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="geo-measure-api",
    description="API for extracting features and calculating area/length measurements from geospatial files.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Health check endpoint to verify backend service status."""
    return HealthResponse(status="ok", message="geo-measure-api is healthy")
