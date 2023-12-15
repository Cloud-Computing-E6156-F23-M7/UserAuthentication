FROM python:3.9.6
WORKDIR /feedback
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
EXPOSE 6062
COPY . .
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "wsgi:app", "-b", "0.0.0.0:6062"]
CMD ["uvicorn", "feedback:app", "--host", "0.0.0.0", "--port", "6062", "--reload", "--log-level", "debug"]
