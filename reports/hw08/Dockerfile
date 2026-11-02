FROM python:3.12-slim
WORKDIR /code
# to show print output in docker logs
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY worker ./worker