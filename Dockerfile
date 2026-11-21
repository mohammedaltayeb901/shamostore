FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p instance

EXPOSE 8000

CMD ["sh", "-c", "flask --app app init-db && gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --access-logfile - wsgi:application"]
