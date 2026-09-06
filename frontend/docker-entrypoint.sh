#!/bin/sh
# O Railway define $PORT só em runtime, e o nginx não lê variável de ambiente
# no arquivo de configuração. Substituímos antes de subir.
set -e
export PORT="${PORT:-8080}"
envsubst '${PORT}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
