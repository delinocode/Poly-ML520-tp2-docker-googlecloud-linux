FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


ENV UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1

WORKDIR /app

# TODO(LAB): install the dependencies from the lock file.
#            Dev-only dependencies have should not be in a production image

# TODO(LAB): copy in what the service needs at runtime: the code, the configuration,
#            the entrypoint and the trained model.


EXPOSE 8000

# We use ENTRYPOINT rather than CMD because this image is the service.
# `docker run <image> bash` must not turn it into something else.
ENTRYPOINT ["scripts/entrypoint.sh"]
