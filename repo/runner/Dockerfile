FROM python:3.11-slim

WORKDIR /runner

COPY . .
RUN pip install --upgrade pip && pip install -e .[dev]

ENV PYTHONPATH=/runner

CMD ["uvicorn", "runner.main:app", "--host", "0.0.0.0", "--port", "8090"]
