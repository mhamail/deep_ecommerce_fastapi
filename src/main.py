# Initialize the FastAPI app with the custom lifespan
from fastapi import FastAPI

from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import (
    userRoute,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Runs once on startup ---
    # print("🟢 Checking if tables exist...")

    # # Create all tables that are missing (safe – only creates non-existent ones)
    # SQLModel.metadata.create_all(engine)
    # print("✅ All tables verified / created.")
    # # --- Runs once on shutdown ---
    # print("🔴 App shutting down...")

    yield  # 👈 after this, FastAPI starts handling requests


app = FastAPI(lifespan=lifespan, root_path="/api")
# Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
    ],  # or "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Hello, FastAPI with uv!"}
