"""
— FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from api.routes import onboarding, hunter, pipeline

app = FastAPI(title="AI Job Agent", version="1.0.0")

# Allow browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(onboarding.router)
app.include_router(hunter.router)
app.include_router(pipeline.router)

# Serve outputs folder for PDF downloads
Path("./outputs").mkdir(exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


@app.get("/")
async def serve_ui():
    """Serve the frontend."""
    return FileResponse("ui/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}