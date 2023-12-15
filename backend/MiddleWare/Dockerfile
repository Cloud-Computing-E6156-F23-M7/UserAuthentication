FROM python:3.9.6
WORKDIR /MiddleWare
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
EXPOSE 8084
COPY . .
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "wsgi:app", "-b", "0.0.0.0:8084"]
CMD ["uvicorn", "MiddleWare:app", "--host", "0.0.0.0", "--port", "8084"]
