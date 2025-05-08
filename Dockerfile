FROM python:3.9-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m spacy download uk_core_news_sm

CMD ["sh", "-c", "flask db upgrade && flask run --host=0.0.0.0"]