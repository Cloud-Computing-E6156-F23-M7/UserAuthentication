#FastAPI Authentication + SiteMgmt

#To run without docker, simply run the app.py. 
#No need to run SiteMgmt/backend/app.py separately

#For running on docker

# create virtual environment
source venv/bin/activate

#activate it 
source venv/bin/activate

# build docker image
docker build -t dockerimage .

#run docker container
docker run -p 8084:8084 dockerimage