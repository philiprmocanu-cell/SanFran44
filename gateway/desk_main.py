"""Standalone Deal Desk server (for the public hosted version)."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from desk import router

app = FastAPI()
app.include_router(router)
app.mount("/", StaticFiles(directory="static/desk", html=True), name="desk")
