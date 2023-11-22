from datetime import datetime, timedelta
import jwt
import os
import requests
from flask import Flask, session, abort, redirect, request, render_template, jsonify
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import secrets
from functools import wraps
from flask_cors import CORS #added

app = Flask("Google Login App")
#app.secret_key = "APP_SECRET_KEY"
app.secret_key = secrets.token_hex(16)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


## Configuration for the Flask-SQLAlchemy extension
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sitemgmt.db'  # You can adjust this according to your database configuration
app.config['SQLALCHEMY_BINDS'] = {
    'sitemgmt_db': 'sqlite:///site_mgmt.db'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB_URI = "http://127.0.0.1:5000"
APP_PORT = 8080

CORS(app) #added

## JWT Configuration
JWT_SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

## Google SSO Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
client_secrets_file = os.path.join("client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email",
            "openid"],
    redirect_uri="http://localhost:"+str(APP_PORT)+"/callback"
)


def login_is_required(function):
    """
    login_is_required: method to check if requests require active Google SSO session
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


def encode_jwt(user_info):
    """
    encode_jwt: creates an encoded JWT token provided user information
    """
    expire_time = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    user_info["exp"] = expire_time
    return jwt.encode(user_info, JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_jwt(encoded_jwt):
    """
    decode: decodes a JWT token
    """
    return jwt.decode(encoded_jwt, JWT_SECRET_KEY, algorithms=[ALGORITHM])


@app.route("/login")
def login():
    """
    login: initializes login state and returns redirected URL to Google SSO
    """
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    """
    callback: rerouted page after logging in that handles Google SSO and encoding of JWT token
    """
    flow.fetch_token(authorization_response=request.url)

    if not session.get("state") == request.args.get("state"):
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

    # ## ADD admin code (if needed)
    # test_admin = {
    #     'admin_id': 1,
    #     'email': "kl3374@columbia.edu",
    #     'isDeleted': 0
    # }
    #
    # response = add_admin(test_admin)
    # print("RESP: ", response)

    response = requests.post(DB_URI+"/api/admin/check/",
        json = {"email": id_info.get("email")})

    if response.status_code != 200:
        abort(401)  # Unauthorized

    admin = response.json()

    if isinstance(admin, tuple):
        error_message, error_code = admin
        if error_code == 404:
            return jsonify({"error": "User not found in administrators database"}), 404
        else:
            return jsonify({"error": f"Error {error_code}: {error_message}"}), error_code

    # For every other admin resource, pass session["admin_id"]
    session["admin_id"] = admin["admin_id"]

    # Encode user information into JWT
    encoded_jwt = encode_jwt({"google_id": id_info.get("sub"), "name": id_info.get("name")})
    print("encoded_jwt: ", encoded_jwt)
    session["jwt_token"] = encoded_jwt
    return redirect("/protected_area")


@app.route("/logout")
def logout():
    """
    logout: user can choose to clear the session by logging out
    """
    session.clear()
    return redirect("/")


@app.get("/")
def index():
    """
    index: returns home landing page for where users can choose to log in
    """
    return render_template(
        "index.html"
    )


##
@app.route("/protected_area")
@login_is_required
def protected_area():
    """
    protected_area: decodes JWT to get user information and routes user to admin landing page
    """
    decoded_jwt = decode_jwt(session["jwt_token"])
    user_name = decoded_jwt.get("name")
    print("decoded_jwt: ", decoded_jwt)
    return render_template(
        "protected_area.html",
        user_name=user_name
    )

@app.route("/add_admin")
@login_is_required
def add_admin_form():
    """
    protected_area: decodes JWT to get user information and routes user to admin landing page
    """
    decoded_jwt = decode_jwt(session["jwt_token"])
    user_name = decoded_jwt.get("name")
    print("decoded_jwt: ", decoded_jwt)
    return render_template(
        "add_admin_form.html",
        server_url=DB_URI
    )

# remote API requests to SiteMgmt DB
def make_remote_request(endpoint, method='GET', data=None):
    try:
        if method == 'GET':
            response = requests.get(f"{DB_URI}/{endpoint}")
        elif method == 'POST':
            response = requests.post(f"{DB_URI}/{endpoint}", json=data)
        elif method == 'PUT':
            response = requests.put(f"{DB_URI}/{endpoint}", json=data)
        elif method == 'DELETE':
            response = requests.delete(f"{DB_URI}/{endpoint}")
        else:
            return jsonify({"error": "Invalid request method"}), 400
        response.raise_for_status()  # Raise an error for bad responses (4xx and 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}") # Handle exceptions (e.g., network errors)
        return jsonify({"error": f"Failed to fetch data from the remote API: {e}"}), 500  # Return an error response with status code 500


# Reset database route
@app.route('/api/reset/sitemgmt/', methods=['PUT'])
#@login_is_required
def reset_sitemgmt_db():
    #decoded_jwt = decode_jwt(session["jwt_token"])
    #user_name = decoded_jwt.get("name")
    return make_remote_request('api/reset/sitemgmt/', method='PUT')

# Admin resource routes
@app.route('/api/admin/', methods=['GET'])
#@login_is_required
def get_all_admin():
    #decoded_jwt = decode_jwt(session["jwt_token"])
    #user_name = decoded_jwt.get("name")
    return make_remote_request('api/admin/', method='GET')

@app.route('/api/admin/<int:admin_id>/', methods=['GET'])
def get_admin(admin_id):
    return make_remote_request(f'api/admin/{admin_id}/', method='GET')

@app.route('/api/admin/check/', methods=['POST'])
def check_email():
    return make_remote_request('api/admin/check/', method='POST', data=request.json)

@app.route('/api/admin/', methods=['POST'])
def add_admin():
    return make_remote_request('api/admin/', method='POST', data=request.json)

@app.route('/api/admin/<int:admin_id>/', methods=['DELETE'])
def delete_admin(admin_id):
    return make_remote_request(f'api/admin/{admin_id}/', method='DELETE')

@app.route('/api/admin/<int:admin_id>/', methods=['PUT'])
def update_admin(admin_id):
    return make_remote_request(f'api/admin/{admin_id}/', method='PUT', data=request.json)

# Feedback resource route, this should only be used on SiteMgmt
@app.route('/api/feedback/', methods=['POST'])
def add_feedback():
    return make_remote_request('api/feedback/', method='POST', data=request.json)

# Feedback resources that are only authorized for admin route
@app.route('/api/feedback/<int:feedback_id>/')
def get_feedback(feedback_id):
    return make_remote_request(f'api/feedback/{feedback_id}/', method='GET')

@app.route('/api/feedback/<int:feedback_id>/', methods=['PUT'])
def update_feedback(feedback_id):
    return make_remote_request(f'api/feedback/{feedback_id}/', method='PUT', data=request.json)

@app.route('/api/feedback/<int:feedback_id>/', methods=['DELETE'])
def delete_feedback(feedback_id):
    return make_remote_request(f'api/feedback/{feedback_id}/', method='DELETE')

@app.route('/api/admin/feedback/')
def get_all_feedback():
    return make_remote_request('api/admin/feedback/', method='GET')

# Action resource only authorized for admin routes
@app.route('/api/admin/action/<int:action_id>/')
def get_action(action_id):
    return make_remote_request(f'api/admin/action/{action_id}/', method='GET')

@app.route('/api/admin/action/')
def get_all_action():
    return make_remote_request('api/admin/action/', method='GET')

@app.route('/api/admin/<int:admin_id>/feedback/<int:feedback_id>/', methods=['POST'])
def add_action(admin_id, feedback_id):
    return make_remote_request(f'api/admin/{admin_id}/feedback/{feedback_id}/', method='POST', data=request.json)

@app.route('/api/admin/action/<int:action_id>/', methods=['PUT'])
def update_action(action_id):
    return make_remote_request(f'api/admin/action/{action_id}/', method='PUT', data=request.json)

@app.route('/api/admin/action/<int:action_id>/', methods=['DELETE'])
def delete_action(action_id):
    return make_remote_request(f'api/admin/action/{action_id}/', method='DELETE')

if __name__ == "__main__":
    app.run(port=APP_PORT, debug=True)
