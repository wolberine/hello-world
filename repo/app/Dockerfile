FROM python:3.11-slim

WORKDIR /app

COPY . .
RUN pip install --upgrade pip && pip install -e .[dev]

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
