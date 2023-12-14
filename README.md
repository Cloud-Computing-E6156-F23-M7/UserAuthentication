#FastAPI Authentication + SiteMgmt

#To run without docker, simply run the app.py. 
#No need to run SiteMgmt/backend/app.py separately

# For Running on Docker all 3 Microservices
```cd backend```

```docker-compose up```

# Activate virtual environment
```source venv/bin/activate```

# build docker image
docker build -t dockerimage .

#run docker container
docker run -p 8084:8084 dockerimage
