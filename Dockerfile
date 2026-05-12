FROM python:3.14-slim

WORKDIR /app

COPY . .

EXPOSE 8000

CMD ["python3", "scripts/dev_server.py", "--host", "0.0.0.0", "--port", "8000"]
