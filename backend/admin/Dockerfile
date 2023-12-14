FROM python:3.9.6
WORKDIR /admin
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
EXPOSE 6061
COPY . .
CMD ["uvicorn", "admin_cp:app", "--host", "0.0.0.0", "--port", "6061", "--reload", "--log-level", "debug"]
