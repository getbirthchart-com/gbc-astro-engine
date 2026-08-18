# syntax=docker/dockerfile:1

# Ephemeris data is deliberately NOT baked into this image. Swiss Ephemeris
# files and JPL kernels carry redistribution terms, and an image that embeds
# them cannot be pushed to a shared registry without checking those terms.
# Mount them at runtime instead -- see docs/DEPLOYMENT.md.

FROM python:3.12-slim AS builder

WORKDIR /build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY src/ ./src/

# Build a wheel so the runtime stage carries no build toolchain.
RUN python -m pip install --upgrade build \
    && python -m build --wheel --outdir /dist


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    GBC_SWISS_EPHE_PATH=/opt/gbc/ephemeris/swiss \
    GBC_JPL_EPHEMERIS_PATH=/opt/gbc/ephemeris/jpl/de440s.bsp

# pyswisseph has no manylinux wheel for this image; compile it here then drop the toolchain.
RUN --mount=type=bind,from=builder,source=/dist,target=/dist \
    apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && python -m pip install "$(ls /dist/*.whl)[api,swiss]" \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Run as a non-root user. Nothing here writes to disk at runtime.
RUN useradd --system --create-home --uid 10001 gbc \
    && mkdir -p /opt/gbc/ephemeris \
    && chown -R gbc:gbc /opt/gbc

USER gbc
WORKDIR /home/gbc
EXPOSE 8000

# Readiness, not liveness: a container without its ephemeris data starts
# perfectly and then fails every chart request. This makes that a deploy
# failure rather than a user-facing one.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "gbc_astro.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
