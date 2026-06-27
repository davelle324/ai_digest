FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv --no-cache-dir

# Copy project files
COPY pyproject.toml .
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Install dependencies
RUN uv pip install --system -e .

# Create data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
