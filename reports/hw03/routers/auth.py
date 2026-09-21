from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND
import time


# Create a router object
# This behaves like a mini FastAPI app
router = APIRouter()

# Configure Jinja2 templates directory
templates = Jinja2Templates(directory="templates")


# Hardcoded credentials for demo purposes only
# In real applications, credentials come from a database
VALID_USERNAME = "admin"
VALID_PASSWORD = "password"

def idle(request:Request) -> bool:
    last_activity = request.session.get("last_activity")
    #user not logged in yet so always false
    if last_activity is None:
        return False
    seconds_count = time.time() - last_activity
    return seconds_count > 60

@router.get("/")
def home(request: Request):
    """
    Home page route.

    - Checks if a user is logged in using the session
    - Passes user info to the template
    """
    user = request.session.get("user")

    return templates.TemplateResponse(
        
        request=request,
        name="index.html",
        context={
            "user": user
        }
    )


@router.get("/login")
def login_page(request: Request):
    """
    Displays the login form.

    If the user is already logged in,
    the template can choose what to display.
    """
    user = request.session.get("user")
    
    #implementing error message
    error = request.session.pop("login_error", None)

    return templates.TemplateResponse(
        request= request,
        name="login.html",
        context={
            "user": user,
            "error": error
        }
    )


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Handles login form submission.

    - Reads username and password from the form
    - Validates credentials
    - Stores user info in session if valid
    """
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        # Store logged-in user in session
        request.session["user"] = username
        #start counting how long user has been idle
        request.session["last_activity"] = time.time()

        # Redirect user to dashboard
        return RedirectResponse(
            url="/dashboard",
            status_code=HTTP_302_FOUND
        )

    # If credentials are invalid:
    # Redirect back to login page
    #
    # No error message is shown intentionally.
    # Students are expected to add Bootstrap alerts.
    request.session["login_error"] = "Invalid user or password"
    return RedirectResponse(
        url="/login",
        status_code=HTTP_302_FOUND
    )


@router.get("/dashboard")
def dashboard(request: Request):
    """
    Protected route.

    - Only accessible if user is logged in
    - Redirects to login page if session is missing
    """
    user = request.session.get("user")

    # If user is not logged in, block access
    if not user:
        return RedirectResponse(
            url="/login",
            status_code=HTTP_302_FOUND
        )

    #time user out and redirect to login
    if idle(request):
        request.session.clear()
        return RedirectResponse(
            url="/login",
            status_code=HTTP_302_FOUND
        )
    #update how long user has been idle if active within the 60 sec count
    request.session["last_activity"] = time.time()
    # If user is logged in, render dashboard
    return templates.TemplateResponse(
        request=request,
        name= "dashboard.html",
        context={
            "user": user
        }
    )


@router.get("/logout")
def logout(request: Request):
    """
    Logs the user out.

    - Clears all session data
    - Redirects back to home page
    """
    request.session.clear()

    return RedirectResponse(
        url="/",
        status_code=HTTP_302_FOUND
    )
