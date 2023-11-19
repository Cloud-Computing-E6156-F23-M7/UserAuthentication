# FlaskAppGoogleSSO

The purpose of this microservice is for admin authentication into the application. The user authentication implements Google SSO and the handing of a JWT token. After a user has logged in, a JWT token is created and that token is subsequently included in future requests to validate that the user is still signed in.

To run the service, navigate over to `backend/app.py` and click the play button to run the service. Navigate over to the URL displayed (`localhost:8080`) in the console where you are prompted to log in. 


#### Testing
For testing valid admins upon login, the current method is importing methods directly from the slightly modified`DbQuery/backend/app.py`. 
Run this file as well concurrently with the other file.
If testing with your Google account, make sure you have added your user into the database prior. There is a code snippet within
this repository's `backend/app.py` showing how to manually add a user.

#### Additional Notes
When logging in via Google SSO, you MAY experience the following:
```
KeyError: 'state'
```
If so, to work around this, try logging into your Columbia Gmail using Incognito.
