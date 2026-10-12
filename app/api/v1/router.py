"""Versioned API v1 router composition."""

from fastapi import APIRouter

from app.api.v1.routes import products
from app.api.v1.routes import auth, health

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(products.router)
api_v1_router.include_router(health.router)
