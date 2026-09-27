#!/bin/sh
# nginx não lê variável de ambiente na config; substitui antes de subir.
set -e
export PORT="${PORT:-8080}"
envsubst '${PORT}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
