# Build em duas etapas: Node compila, nginx serve. A imagem final não leva Node.
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Build arg, não variável de runtime: o Vite embute o valor no bundle.
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine
RUN apk add --no-cache gettext
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/nginx.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.d/entrypoint.sh
RUN rm /etc/nginx/conf.d/default.conf
ENTRYPOINT ["/docker-entrypoint.d/entrypoint.sh"]
