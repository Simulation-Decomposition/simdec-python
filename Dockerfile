## Step 1/3: Base image
FROM python:3.12-alpine as base

## Step 2/3: Build/Install app dependencies
FROM base as builder
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=True

COPY pyproject.toml README.md /

RUN --mount=type=cache,mode=0777,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install -e ".[dashboard]"  && \
    mkdir -p /app/src

COPY src /app/src
COPY tests/data /app/tests/data
COPY panel /app/panel
COPY docs/_static /app/_static

# Step 3/3: Image
FROM  base as panel
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=True
ENV PYTHONPATH=/app/src
ENV PYTHONIOENCODING=utf-8
ENV MPLCONFIGDIR=/tmp/matplotlib
EXPOSE 8080

COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/panel /usr/local/bin/panel
COPY --from=builder /app /app

RUN addgroup -S app && adduser -S app -G app

USER app
WORKDIR /app

# Run the web service on container startup.
CMD ["panel", "serve", "panel/app.py", \
     "--address", "0.0.0.0", "--port", "8080", \
     "--num-procs", "2", \
     "--allow-websocket-origin", "simdec.io", \
     "--allow-websocket-origin", "www.simdec.io", \
     "--allow-websocket-origin", "simdec-panel-h6musew72q-lz.a.run.app", \
     "--cookie-secret", "panel_cookie_secret_oauth", \
     "--logout-template", "panel/logout.html", \
     "--oauth-provider", "google", \
     "--static-dirs", "_static=_static", \
     "--reuse-sessions", "--warm"]
