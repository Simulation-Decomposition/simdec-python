## Step 1/3: Base image
FROM python:3.11-slim-bookworm as base
RUN \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get upgrade -y && apt install curl -y

## Step 2/3: Build/Install app dependencies
FROM base as builder
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

COPY pyproject.toml README.md /

RUN --mount=type=cache,target=/var/cache/apt apt install -y gcc git
RUN --mount=type=cache,mode=0777,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install -e .  && \
    mkdir -p /app/src

COPY src /app/src
COPY tests/data /app/tests/data
COPY panel /app/panel
COPY docs/_static /app/_static

# Step 3/3: Image
FROM  base as panel
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True
ENV PYTHONPATH=/app/src
ENV PYTHONIOENCODING=utf-8
ENV ENV=production
ENV MPLCONFIGDIR=/tmp/matplotlib
EXPOSE 8080

COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/panel /usr/local/bin/panel
COPY --from=builder /app /app

RUN useradd app && usermod -a -G app app
USER app
WORKDIR /app

# Run the web service on container startup.
CMD ["panel", "serve", "panel/app.py", \
     "--address", "0.0.0.0", "--port", "8080", "--num-procs", "1", "--allow-websocket-origin", "*", \
     "--cookie-secret", "panel_cookie_secret", \
     "--basic-login-template", "panel/login.html", \
     "--logout-template", "panel/logout.html", \
     "--static-dirs", "_static=_static"]
