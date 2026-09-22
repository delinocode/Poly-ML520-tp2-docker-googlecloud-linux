FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


ENV UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1

WORKDIR /app

# TODO(LAB): install the dependencies from the lock file.
#            Dev-only dependencies have should not be in a production image

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# TODO(LAB): copy in what the service needs at runtime: the code, the configuration,
#            the entrypoint and the trained model.

COPY src/ src/
COPY configs/ configs/
COPY scripts/entrypoint.sh scripts/
COPY out/models/model.joblib out/models/
RUN uv sync --frozen --no-dev
RUN chmod +x scripts/entrypoint.sh

EXPOSE 8000

# We use ENTRYPOINT rather than CMD because this image is the service.
# `docker run <image> bash` must not turn it into something else.
ENTRYPOINT ["scripts/entrypoint.sh"]
