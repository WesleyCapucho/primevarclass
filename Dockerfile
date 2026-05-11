FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PRIMEVARCLASS_JOB_ROOT=/app/primevarclass_job_history

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY docs ./docs
COPY configs ./configs
COPY data/examples ./data/examples

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "primevarclass.api:app", "--host", "0.0.0.0", "--port", "8000"]
