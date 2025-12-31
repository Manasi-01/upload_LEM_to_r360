from fastapi import FastAPI
from app.routes.upload import router as upload_router

app = FastAPI(
    title="PSD API",
    description="API for extracting PSD numbers and fetching parent IDs",
    version="1.0.0"
)

app.include_router(upload_router)
