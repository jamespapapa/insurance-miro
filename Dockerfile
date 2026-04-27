FROM node:24-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM python:3.11

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    FLASK_HOST=0.0.0.0 \
    FLASK_DEBUG=False

COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --frozen --no-install-project

COPY backend ./backend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

RUN mkdir -p backend/uploads/projects backend/uploads/simulations backend/uploads/reports

EXPOSE 5001

CMD ["sh", "-c", "cd backend && uv run python run.py"]
