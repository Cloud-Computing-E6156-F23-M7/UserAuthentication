# FastAPI Authentication + SiteMgmt

# For Running with Docker all 3 Microservices
```cd backend```

```docker-compose up```

# To run without docker
### Activate virtual environment
```source venv/bin/activate```

``` pip install -r requirements.txt```

``` cd backend ```

### Run the files

```python3 admin/admin.py ```

```python3 feedback/feedback.py```

```python3 MiddleWare/MiddleWare.py ```

# Note about SiteMgmt
Make sure to run ```SiteMgmt/backend/app.py``` separately either with docker or without

When testing locally and not on the cloud, running UserAuth with docker will not work (docker can't run when APIs are calling localhost on separate docker containers)


