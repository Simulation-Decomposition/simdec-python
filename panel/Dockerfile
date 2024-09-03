## Step 1/3: Base image
FROM python:3.12-alpine as base

## Step 2/3: Build/Install app dependencies
FROM base as builder
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=True
ENV PYTHONDONTWRITEBYTECODE=true

COPY pyproject.toml README.md /

RUN --mount=type=cache,mode=0777,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -e ".[dashboard]"

RUN find /usr/local/lib/python3.12/site-packages -name "test" -depth -type d -exec rm -rf '{}' \;
RUN find /usr/local/lib/python3.12/site-packages -name "tests" -depth -type d -exec rm -rf '{}' \;
RUN find /usr/local/lib/python3.12/site-packages -name "docs" -depth -type d -exec rm -rf '{}' \;
RUN find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

RUN rm -rf /usr/local/lib/python3.12/site-packages/panel/dist/bundled/deckglplot
RUN rm -rf /usr/local/lib/python3.12/site-packages/panel/dist/bundled/abstractvtkplot
RUN rm -rf /usr/local/lib/python3.12/site-packages/panel/dist/bundled/aceplot
RUN rm -rf /usr/local/lib/python3.12/site-packages/panel/dist/bundled/bootstrap5
RUN rm -rf /usr/local/lib/python3.12/site-packages/panel/dist/bundled/plotlyplot
RUN rm -rf /usr/local/lib/python3.12/site-packages/panel/dist/bundled/bootstrap4

# stats depends on spatial, special, sparse, linalg, ndimage, fft
RUN rm -rf /usr/local/lib/python3.12/site-packages/scipy/signal
RUN rm -rf /usr/local/lib/python3.12/site-packages/scipy/misc
RUN rm -rf /usr/local/lib/python3.12/site-packages/scipy/cluster

RUN mkdir -p /app/src
COPY src /app/src
COPY tests/data /app/tests/data
COPY panel /app/panel
COPY docs/_static /app/_static

# Step 3/3: Image
FROM  base as panel
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=True
ENV PYTHONDONTWRITEBYTECODE=true
ENV PYTHONPATH=/app/src
ENV PYTHONIOENCODING=utf-8
ENV MPLCONFIGDIR=/tmp/matplotlib
EXPOSE 8080

COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/panel /usr/local/bin/panel
COPY --from=builder /app /app

# Basic security hardening
RUN rm -rf /usr/local/lib/python3.12/site-packages/pip
RUN rm -rf /usr/local/lib/python3.12/site-packages/wheel
RUN rm -rf /usr/local/lib/python3.12/site-packages/setuptools
RUN apk --purge del apk-tools

RUN addgroup -S app && adduser -S app -G app

USER app
WORKDIR /app

# Run the web service on container startup.
CMD ["panel", "serve", "panel/simdec_app.py", "panel/sampling.py", \
     "--address", "0.0.0.0", "--port", "8080", \
     "--num-procs", "2", \
     "--allow-websocket-origin", "simdec.io", \
     "--allow-websocket-origin", "www.simdec.io", \
     "--allow-websocket-origin", "simdec-panel-h6musew72q-lz.a.run.app", \
     "--cookie-secret", "panel_cookie_secret_oauth", \
     "--basic-login-template", "panel/login.html", \
     "--logout-template", "panel/logout.html", \
     "--oauth-provider", "custom_google", \
     "--index", "panel/index.html", \
     "--static-dirs", "_static=_static", \
     "--reuse-sessions", "--warm", \
     "--global-loading-spinner"]
