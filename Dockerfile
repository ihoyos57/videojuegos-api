FROM python:3.11-slim

WORKDIR /app
ARG APP_VERSION=2.0.1
ENV APP_VERSION=${APP_VERSION}
ENV APP_TRACK=stable

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
