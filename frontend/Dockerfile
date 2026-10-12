# Build em duas etapas: Node compila, nginx serve. A imagem final não leva Node.
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Build args, não variáveis de runtime: o Vite embute os valores no bundle. No Railway, as
# variáveis do serviço chegam aqui como build args, mas só as declaradas com ARG.
ARG VITE_API_URL=
ARG VITE_FIREBASE_API_KEY=
ARG VITE_FIREBASE_AUTH_DOMAIN=
ARG VITE_FIREBASE_PROJECT_ID=
ENV VITE_API_URL=$VITE_API_URL \
    VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY \
    VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN \
    VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID
RUN npm run build

FROM nginx:alpine
RUN apk add --no-cache gettext
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/nginx.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.d/entrypoint.sh
RUN rm /etc/nginx/conf.d/default.conf
ENTRYPOINT ["/docker-entrypoint.d/entrypoint.sh"]
