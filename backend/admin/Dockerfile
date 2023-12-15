FROM python:3.9.6
WORKDIR /admin
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
EXPOSE 6061
COPY . .
#CMD ["gunicorn", "wsgi:app", "-w 4", "-b 0.0.0.0:6061", "-t 30"]
#CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "wsgi:app", "-b", "0.0.0.0:6061"]
#CMD ["uvicorn", "admin:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "6061"]
CMD ["uvicorn", "admin:app", "--host", "0.0.0.0", "--port", "6061"]
