FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first for layer caching. All ML/physics libs ship manylinux wheels
# for cp312, so no system build toolchain is required.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Ensure mounted data/model dirs exist even if the volumes are empty.
RUN mkdir -p /app/data/raw/kaggle /app/data/raw/substations /app/data/processed /app/models

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
