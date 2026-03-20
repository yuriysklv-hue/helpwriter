"""
HelpWriter API — FastAPI application.
Serves REST API for the web editor frontend.
"""

import os
import sys

# Add project root to path so database.py is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth, documents, folders, users, internal

WEB_URL = os.getenv("WEB_URL", "http://localhost:5173")

app = FastAPI(
    title="HelpWriter API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

# CORS — allow requests from the frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEB_URL],
    allow_credentials=True,  # Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(folders.router, prefix="/api/folders", tags=["folders"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(internal.router, prefix="/internal", tags=["internal"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
