FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları (Prophet için gerekli)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/raw data/processed models logs reports

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
