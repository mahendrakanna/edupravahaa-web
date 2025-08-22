FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

COPY dist/requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /code/

RUN mkdir -p /code/dist/media /code/dist/static
RUN chmod -R 777 /code/dist/media /code/dist/static

CMD ["python", "dist/manage.py", "runserver", "0.0.0.0:8000"]