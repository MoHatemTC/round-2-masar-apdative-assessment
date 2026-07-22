# Adaptive Assessment — backend (FastAPI + Uvicorn).
# No database container here on purpose: the DB is remote Supabase (see docker-compose.yml's
# comment on this) — this image only ever talks to it over the network via SUPABASE_URL/KEY.
FROM python:3.12-slim

WORKDIR /app

# build-essential covers the rare case a dependency (or a future one) needs to compile from
# source instead of using a prebuilt wheel. Removed in the same layer it's used in isn't done
# here since pip still needs it at the RUN step below within this single stage — an acceptable
# trade of a slightly larger image for install reliability across platforms.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY the dependency manifest first. Docker caches each layer keyed on its inputs, so this
# `pip install` layer is only re-run when requirements.txt itself changes — editing application
# code (copied below) won't force a slow full reinstall on every rebuild.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now bring in the actual application code.
COPY . .

# Run as a non-root user. If something inside the container is ever compromised, it shouldn't
# also hand over root on whatever host is running this image.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# NOTE: no --reload here — that's a dev-only flag. This is the production/deployable image;
# for local hot-reload development, run uvicorn with --reload directly on your host instead.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]