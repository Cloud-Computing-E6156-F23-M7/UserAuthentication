import os
import uvicorn
import jwt
import json
from json import JSONDecodeError
import httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi_sso.sso.google import GoogleSSO
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.templating import Jinja2Templates

# Google SSO and JWT Configuration
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
App_port = 8084
with open('../../client_secret.json') as json_file:
    data = json.load(json_file)
    CLIENT_ID = data['web']['client_id']
    CLIENT_SECRET = data['web']['client_secret']
    REDIRECT_URI = "http://localhost:" + str(App_port) + "/callback"

sso = GoogleSSO(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    allow_insecure_http=True,
)


JWT_SECRET_KEY = "09d25e094faa6ca2556c818166b"+\
"7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
session = {"jwt_token": None,
            "google_id": None,
            "email": None,
            "name": None,
            "admin_id": None}

ADMIN_SERVICE_URL = "http://18.222.192.226:6061"
FEEDBACK_SERVICE_URL = "http://18.222.192.226:6062"


# Middleware for JWT Authentication
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/" or \
        request.url.path.startswith("/login") or\
        request.url.path.startswith("/callback") or\
        request.url.path.startswith("/protected_area") or\
        request.url.path.startswith("/logout"):
            return await call_next(request)

        if request.url.path.startswith('/api/admin') \
        and not request.url.path.startswith('/api/admin/check'):
            try:
                payload = jwt.decode(session["jwt_token"],
                                         JWT_SECRET_KEY, algorithms=[ALGORITHM])
                if payload["admin_id"] == None:
                    return JSONResponse(status_code=403,
                                    content={"message": "You're not an admin"})
            except jwt.ExpiredSignatureError:
                return JSONResponse(status_code=403,
                                    content={"message": "Your JWT has expired"})
            except jwt.PyJWTError:
                return JSONResponse(status_code=403,
                                    content={"message": "Please log in to proceed"})

        if request.url.path.startswith("/api/admin"):
            service_url = ADMIN_SERVICE_URL
        elif request.url.path.startswith("/api/feedback"):
            service_url = FEEDBACK_SERVICE_URL
        else:
            return JSONResponse(status_code=400, content={"message": "Bad request"})


        request_body = await request.body()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=request.method,
                    url=f"{service_url}{request.url.path}",
                    headers=request.headers,
                    content=request_body,
                    params=request.query_params
                )
                if response.status_code == httpx.codes.OK:
                    return JSONResponse(status_code=response.status_code,
                                        content=response.json())
                else:
                    return JSONResponse(status_code=response.status_code,
                                        content=response.text)
        except httpx.RequestError as exc:
            return JSONResponse(status_code=502, content={"message": "Bad Gateway"})



app = FastAPI()
app.add_middleware(AuthMiddleware)
templates = Jinja2Templates(directory="templates")


# Helper function to generate JWT
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


def error_page(request: Request,
    error_message="Login is Required to access this page"):
    return templates.TemplateResponse("error_page.html",
        {"request": request, "error_type": error_message})


@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return "OK"


@app.get("/login/")
async def login():
    with sso:
        return await sso.get_login_redirect(params=\
            {"prompt": "consent", "access_type": "offline"})

async def send_request():
    async with httpx.AsyncClient() as client:
        url = f"{ADMIN_SERVICE_URL}/api/admin/check"
        payload = {"email": session["email"]}
        response = await client.post(url, json=payload)

        if response.status_code == httpx.codes.OK:
            return response.json()
        else:
            return None


@app.get("/callback/", response_class=HTMLResponse)
async def auth_callback(request: Request):
    """Verify login"""
    try:
        with sso:
            user = await sso.verify_and_process(request)
            session["google_id"] = user.id
            session["email"] = user.email
            session["name"] = user.display_name

            # TODO: Send Request to check admin
            response = await send_request()

            if response is None:
                raise HTTPException(status_code=401,
                                    detail="You're not an admin")

            session["admin_id"] = response["adminId"]

            encoded_jwt = encode_jwt({"google_id": session["google_id"],
                                     "name": session["name"],
                                     "email": session["email"],
                                     "admin_id": session["admin_id"]})

            if isinstance(encoded_jwt, tuple):
                raise HTTPException(status_code=401, detail="Invalid token")

            session["jwt_token"] = encoded_jwt

            return RedirectResponse(url="/protected_area/")
    except Exception as e:
        print("The exception is: ", e)
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/protected_area/", response_class=HTMLResponse)
async def protected_area(request: Request):
    return HTMLResponse(content="Reached protected area")


@app.get("/logout/", response_class=HTMLResponse)
async def logout(request: Request):
    session["jwt_token"] = None
    session["google_id"] = None
    session["email"] = None
    session["name"] = None
    session["admin_id"] = None
    return HTMLResponse(content="Successfully Logged out")


if __name__ == "__main__":
    uvicorn.run("MiddleWare:app", host="0.0.0.0", port=App_port, reload=True, log_level="debug")