FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY scripts ./scripts
COPY data ./data
ENV DATABASE_PATH=./data/mock_api.db
ENV SOURCES_MANIFEST=./data/sources.json
RUN python scripts/load_data.py
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
