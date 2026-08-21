#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    exec "$@"
fi

APP_UID="$(stat -c '%u' /app/config)"
APP_GID="$(stat -c '%g' /app/config)"

if [ "$APP_UID" -eq 0 ]; then
    exec "$@"
fi

GROUP_NAME="$(getent group "$APP_GID" | cut -d: -f1 || true)"
if [ -z "$GROUP_NAME" ]; then
    GROUP_NAME="imageprocessor"
    groupadd --gid "$APP_GID" "$GROUP_NAME"
fi

USER_NAME="$(getent passwd "$APP_UID" | cut -d: -f1 || true)"
if [ -z "$USER_NAME" ]; then
    USER_NAME="imageprocessor"
    useradd \
        --uid "$APP_UID" \
        --gid "$APP_GID" \
        --create-home \
        --no-user-group \
        "$USER_NAME"
fi

mkdir -p /tmp/u2net /tmp/numba_cache
chown "$APP_UID:$APP_GID" /tmp/u2net /tmp/numba_cache

exec setpriv \
    --reuid="$APP_UID" \
    --regid="$APP_GID" \
    --init-groups \
    "$@"