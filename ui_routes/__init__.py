# Standard library imports
import logging

# Third-party imports
from fastapi import APIRouter

# Local imports
from .dashboard_routes import router as dashboard_router
from .auth_routes import router as auth_router
from .webauthn_routes import router as webauthn_router

# Create parent router
router = APIRouter()

# Include sub-routers
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(webauthn_router)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)