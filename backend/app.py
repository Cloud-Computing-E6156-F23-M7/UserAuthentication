from datetime import datetime, timedelta
import jwt
import os
import requests
import json
### OLD
'''from flask import Flask, session, abort, redirect, request, render_template, jsonify
from google.oauth2 import id_token
from pip._vendor import cachecontrol
import google.auth.transport.requests'''
from google_auth_oauthlib.flow import Flow
from functools import wraps
###
### NEW
from flask import Flask, render_template, url_for, redirect, session, abort
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
###

#app = Flask(__name__)
app = Flask("Google Login App")
### OLD
#app.secret_key = "APP_SECRET_KEY"
###
app.secret_key = os.urandom(12)
#os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

## Configuration for the Flask-SQLAlchemy extension
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sitemgmt.db'  # You can adjust this according to your database configuration
app.config['SQLALCHEMY_BINDS'] = {
    'sitemgmt_db': 'sqlite:///site_mgmt.db'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB_URI = "http://127.0.0.1:5000"
APP_PORT = 8084


## JWT Configuration
JWT_SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

### NEW
oauth = OAuth(app)
###

### OLD
#GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
## Google SSO Configuration
'''GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
client_secrets_file = os.path.join("client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email",
            "openid"],
    redirect_uri="http://localhost:"+str(APP_PORT)+"/callback"
)'''
###


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


### OLD
'''@app.route("/login")
def login():
    """
    login: initializes login state and returns redirected URL to Google SSO
    """
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)
'''
###

### NEW
@app.route("/login")
def login():

    with open('./client_secret.json') as json_file:
        data = json.load(json_file)
        GOOGLE_CLIENT_ID = data['web']['client_id']
        GOOGLE_CLIENT_SECRET = data['web']['client_secret']

        #GOOGLE_CLIENT_ID = '43804654254-2lhha87esgl2ebqga1vk7rl3dqehk7r2.apps.googleusercontent.com'
        #GOOGLE_CLIENT_SECRET = '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'

    CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    oauth.register(
        name='login',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=CONF_URL,
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    redirect_uri = url_for('callback', _external=True)
    print(redirect_uri)
    session['nonce'] = generate_token()
    return oauth.login.authorize_redirect(redirect_uri, nonce=session['nonce'])
###


### OLD
'''@app.route("/callback")
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
    return redirect("/protected_area")'''
###

### NEW
@app.route("/callback")
def callback():
    """
    callback: rerouted page after logging in that handles Google SSO and encoding of JWT token
    """
    print("Reached the callback function")
    token = oauth.login.authorize_access_token()
    #print("token: ", token)
    user = oauth.login.parse_id_token(token, nonce=session['nonce'])
    session["google_id"] = user
    #print(" Google User ", user)
    session["email"] = user["email"]
    session["name"] = user["name"]

    '''session["google_id"] = id_info.get("sub")
                session["name"] = id_info.get("name")'''

    response = requests.post(DB_URI+"/api/admin/check/",
        json = {"email": session['email']})


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
    encoded_jwt = encode_jwt({"google_id": session["google_id"], "name": session["name"]})
    #encoded_jwt = token["id_token"]
    print("encoded_jwt: ", encoded_jwt)
    session["jwt_token"] = encoded_jwt
    return redirect("/protected_area")
###


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
    print("Got to Protected Area Function")
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

if __name__ == "__main__":
    app.run(port=APP_PORT, debug=True)
