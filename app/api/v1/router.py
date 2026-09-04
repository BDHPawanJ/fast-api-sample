"""Versioned API v1 router composition."""

from fastapi import APIRouter

from app.api.routes import auth, health, products

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(products.router)
api_v1_router.include_router(health.router)
