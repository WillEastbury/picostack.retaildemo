FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY V2 ./V2

EXPOSE 8802

CMD ["python", "-m", "uvicorn", "wavestore_erp_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8802"]
