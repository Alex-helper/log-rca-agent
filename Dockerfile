# Multi-stage: build React, then run FastAPI serving dist
FROM node:20-alpine AS fe
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY docs /app/docs
COPY .env.example /app/.env.example
COPY --from=fe /fe/dist /app/frontend/dist
ENV PYTHONPATH=/app/backend
ENV CACHE_DIR=/app/.cache/rca
EXPOSE 8787
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
