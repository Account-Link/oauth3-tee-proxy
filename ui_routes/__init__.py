# Standard library imports
import logging

# Third-party imports
from fastapi import APIRouter

# Local imports
from .auth_routes import router as auth_router
from .api_routes import router as api_router

# Create parent router
router = APIRouter()

# Include sub-routers
router.include_router(auth_router)
router.include_router(api_router)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)