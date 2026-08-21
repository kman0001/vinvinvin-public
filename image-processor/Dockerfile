FROM python:3.11-slim

WORKDIR /app

ENV U2NET_HOME=/tmp/u2net \
    NUMBA_CACHE_DIR=/tmp/numba_cache \
    ORT_DISABLE_TELEMETRY=1

COPY pyproject.toml .

RUN pip install --no-cache-dir .

COPY . .

RUN chmod -R a+rX /app/app \
    && mkdir -p /tmp/u2net /tmp/numba_cache /app/images \
    && chmod 1777 /tmp/numba_cache

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python3", "-u", "-m", "app.main"]