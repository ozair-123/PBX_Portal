"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Config

# Create FastAPI application
app = FastAPI(
    title="PBX Control Portal API",
    description="Backend API for managing Asterisk PBX users, extensions, and configuration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "PBX Control Portal",
        "version": "1.0.0"
    }


# Register routers
from .api import users, apply

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(apply.router, prefix="/apply", tags=["apply"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
