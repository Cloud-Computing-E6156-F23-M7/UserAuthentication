"""
Google Login Example
"""
import os
import uvicorn
import json
import jwt
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Form, Depends, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_sso.sso.google import GoogleSSO
from starlette.templating import Jinja2Templates

from fastapi.staticfiles import StaticFiles
from functools import wraps

from backend.app import MySQLDataService

#import env

app = FastAPI()
site_mgmt = MySQLDataService()

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
#CLIENT_ID = os.environ["CLIENT_ID"]
#CLIENT_SECRET = os.environ["CLIENT_SECRET"]
#OAUTH_URL = os.environ["OAUTH_URL"]
App_port = 8084
DB_URI = "http://127.0.0.1:8080"
'''
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sitemgmt.db'  
app.config['SQLALCHEMY_BINDS'] = {
    'sitemgmt_db': 'sqlite:///site_mgmt.db'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
'''

with open('./client_secret.json') as json_file:
    data = json.load(json_file)
    CLIENT_ID = data['web']['client_id']
    CLIENT_SECRET = data['web']['client_secret']
    OAUTH_URL = "http://localhost:"+str(App_port)


sso = GoogleSSO(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=OAUTH_URL + "/callback",
    allow_insecure_http=True,
)

## JWT Configuration
JWT_SECRET_KEY = "09d25e094faa6ca2556c818166b"+\
"7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15


templates = Jinja2Templates(directory="templates")

session = {}

# Decorator to ensure the user is logged in
def login_is_required(view_function):
    async def check_login_status(request: Request, *args, **kwargs):
        if "jwt_token" not in request.session:
            return errorPage(request)
        return await view_function(request, *args, **kwargs)
    return RedirectResponse(url="/")


def encode_jwt(user_info):
    """
    encode_jwt: creates an encoded JWT token provided user information
    """
    try:
        expire_time = datetime.utcnow() + \
         timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        user_info["exp"] = expire_time
        return jwt.encode(user_info,
         JWT_SECRET_KEY, algorithm=ALGORITHM)
    except Exception as e:
        return None, f"Error encoding JWT: {e}"


def get_current_user():
    try:
        payload = jwt.decode(session["jwt_token"],
         JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except KeyError:
        return "Login is Required to access this page"
    except jwt.ExpiredSignatureError:
        return "Your session has timed out. "+\
            "Please log in again to access this page"
    return payload


def errorPage(request: Request, 
    error_message="Login is Required to access this page"):
    session = {}
    return templates.TemplateResponse("error_page.html",
        {"request": request, "error_type": error_message})


@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse("index.html",
     context={"request": request})


@app.get("/login")
async def auth_init():
    """Initialize auth and redirect"""
    with sso:
        return await sso.get_login_redirect(params=\
            {"prompt": "consent", "access_type": "offline"})


@app.get("/callback", response_class=HTMLResponse)
async def auth_callback(request: Request):
    """Verify login"""
    try:
        with sso:
            user = await sso.verify_and_process(request)
            data = user
            session["google_id"] = user.id 
            session["email"] = user.email
            session["name"] = user.display_name

            response = site_mgmt.check_email(session["email"])

            if isinstance(response, tuple):
                return errorPage(request, error_message = \
                    "User not found in administrators database")

            session["admin_id"] = response["admin_id"]

            # Encode user information into JWT
            encoded_jwt = encode_jwt({"google_id": session["google_id"],
                                     "name": session["name"],
                                     "email": session["email"],
                                     "admin_id": session["admin_id"]})

            if isinstance(encoded_jwt, tuple):
                return errorPage(request, encoded_jwt[1])

            session["jwt_token"] = encoded_jwt

            return RedirectResponse(url="/protected_area")
    except Exception as e:
        print("The exception is: ", e)
        return errorPage(request, 
            error_message="An error occured during your login")


@app.get("/protected_area", response_class=HTMLResponse)
async def dashboard(request: Request, 
    current_user: dict=Depends(get_current_user)):
    """
    protected_area: decodes JWT to get user 
    information and routes user to admin landing page
    """
    if isinstance(current_user, str):
        return errorPage(request)

    return templates.TemplateResponse("protected_area.html",
     context={"request": request, "user_name": current_user["name"]})


@app.get("/add_admin", response_class=HTMLResponse)
async def render_add_admin_form(request: Request,
 current_user: dict=Depends(get_current_user)):
    """
    add_admin: adds admin with user email to the admin database
    """
    if isinstance(current_user, str):
        return errorPage(request)

    return templates.TemplateResponse(
        "add_admin_form.html", {"request": request})


@app.post("/add_admin", response_class=HTMLResponse)
async def add_admin(request: Request, email: str = Form(...)):
    result = site_mgmt.add_admin(email)

    return templates.TemplateResponse(
        "add_admin_form.html",
        {"request": request, "result": result[0]}
    )


@app.get("/delete_admin", response_class=HTMLResponse)
async def render_delete_admin_form(request: Request,
 current_user: dict=Depends(get_current_user)):
    """
    delete_admin: deletes admin by user email
    """
    if isinstance(current_user, str):
        return errorPage(request)

    return templates.TemplateResponse("delete_admin_form.html",
     {"request": request})


@app.post("/delete_admin", response_class=HTMLResponse)
async def delete_admin(request: Request, email: str = Form(...)):
    result = site_mgmt.delete_admin(email)

    return templates.TemplateResponse(
        "delete_admin_form.html",
        {"request": request, "result": result[0], "email" : email}
    )


@app.get("/update_admin", response_class=HTMLResponse)
async def render_update_admin_form(request: Request,
 current_user: dict=Depends(get_current_user)):
    """
    delete_admin: deletes admin by user email
    """
    if isinstance(current_user, str):
        return errorPage(request)

    return templates.TemplateResponse("update_admin_form.html",
     {"request": request})


@app.post("/update_admin", response_class=HTMLResponse)
async def update_admin(request: Request, old_email: str = Form(...),
    new_email: str = Form(...)):
    result = site_mgmt.update_admin(old_email, new_email)

    return templates.TemplateResponse(
        "update_admin_form.html",
        {"request": request, "result": result[0], 
        "old_email": old_email, "new_email": new_email}
    )


@app.get("/logout", response_class = HTMLResponse)
async def logout(request: Request):
    session = {}
    return RedirectResponse(url="/")


if __name__ == "__main__":
    #uvicorn.run(app, host="0.0.0.0", port=App_port)
    app.run(debug=True, port=App_port)

