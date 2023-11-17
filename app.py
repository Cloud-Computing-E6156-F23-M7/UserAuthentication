from datetime import datetime, timedelta
import jwt
import os
import requests
from flask import Flask, session, abort, redirect, request, render_template
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
#from flask_sqlalchemy import SQLAlchemy
from DbQuery.backend.app import get_admin, Admin, db

app = Flask("Google Login App")
app.secret_key = "CodeSpecialist.com"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


# Set a placeholder value for SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sitemgmt.db'  # You can adjust this according to your database configuration
app.config['SQLALCHEMY_BINDS'] = {
        'sitemgmt_db': 'sqlite:///sitemgmt.db'
    }
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

JWT_SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 5
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
client_secrets_file = os.path.join("./client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://localhost:8080/callback"
)


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


def get_admin_by_email(email):
    return Admin.query.filter_by(email=email).first()

def authenticate_user(email):
    # Check if the user is an admin based on their email
    admin = get_admin_by_email(email)
    if admin:
        return admin

    return None


def encode_jwt(user_info):
    expire_time = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    user_info["exp"] = expire_time
    return jwt.encode(user_info, JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_jwt(encoded_jwt):
    return jwt.decode(encoded_jwt, JWT_SECRET_KEY, algorithms=[ALGORITHM])


@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")


    admin = get_admin(id_info.get("email"))

    if not admin or admin.isDeleted:
        abort(401)  # Unauthorized

    # Encode user information into JWT
    encoded_jwt = encode_jwt({"google_id": id_info.get("sub"), "name": id_info.get("name")})
    print("encoded_jwt: ", encoded_jwt)
    session["jwt_token"] = encoded_jwt
    return redirect("/protected_area")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/")
def index():
    return render_template(
        "index.html"
    )

@app.route("/protected_area")
@login_is_required
def protected_area():
    # Decode JWT to get user information
    decoded_jwt = decode_jwt(session["jwt_token"])
    user_name = decoded_jwt.get("name")
    return render_template(
        "protected_area.html",
        user_name=user_name
    )


if __name__ == "__main__":
    app.run(port=8080, debug=True)