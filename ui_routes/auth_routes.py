# Standard library imports

# Third-party imports
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Set up templates
templates = Jinja2Templates(directory="templates")

# Create router
router = APIRouter(tags=["UI:Authentication"])

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with application introduction and login/register options."""
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """WebAuthn registration page."""
    return templates.TemplateResponse("webauthn_register.html", {"request": request})

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """WebAuthn login page."""
    return templates.TemplateResponse("webauthn_login.html", {"request": request})

@router.get("/error", response_class=HTMLResponse)
async def error_page(request: Request, message: str, back_url: str = "/"):
    """
    Display an error page with a custom message.
    
    Args:
        request (Request): The HTTP request object
        message (str): The error message to display
        back_url (str): The URL to go back to
    """
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error_message": message,
        "back_url": back_url
    })